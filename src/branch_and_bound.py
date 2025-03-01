import sys
import gurobipy as gp
import numpy as np
from operator import attrgetter
from gurobipy import GRB
from dataclasses import dataclass
from src.branching_rules import BranchingRules
import src.bisect_local as bisect


class BranchAndBound:

    @dataclass
    class Stats:
        n: int
        branching_count: int = 0
        int_branching_count: int = 0
        primal_bound: float = -float('inf')
        dual_bound: float = -float('inf')
        known_opt: float = -float('inf')


    class GRBModel:
        def __init__(self, mps_path, presolve):

            self.env = gp.Env(empty=True)
            self.env.setParam("OutputFlag", 0)
            self.env.start()

            self.presolve = presolve
            self.set_model(mps_path)

        def set_model(self, mps_path):
            self.model = gp.read(mps_path, env=self.env)
            self.model.setParam("Seed", 0)
            self.model.setParam("Method", 1) # dual simplex
            if self.presolve: self.model = self.model.presolve()

            self.var = self.model.getVars()

            self.bin_var = [v for v in self.var if v.vtype == 'B' or v.vtype == 'I']
            self.n = len(self.bin_var)

            self.model.update()
            self.changed_sense = 1
            if self.model.ModelSense == 1:
                self.changed_sense = -1
                self.model.ModelSense = -1
                self.model.setObjective(-self.model.getObjective())
                self.model.setParam('LogToConsole', 0)
                self.model.update()


        def solve_lp(self, face):
            for i, x in enumerate(face):
                if x == 0: self.bin_var[i].ub = 0
                elif x == 1: self.bin_var[i].lb = 1

            self.model.optimize()
            val, sol = (round(self.model.objVal, 8), np.fromiter((v.x for v in self.bin_var), float)) if self.model.status == 2 else  (-float('inf'), None)

            for i, x in enumerate(face):
                if x == 0: self.bin_var[i].ub = 1
                elif x == 1: self.bin_var[i].lb = 0
            return val, sol


    class Node:

        def __init__(self, face, grb_model):

            self.x = face
            self.id = 0

            self.ub, self.bin_sol = grb_model.solve_lp(self.x)

            if self.bin_sol is not None:
                self.bin_sol = np.round(self.bin_sol, 8)

            if self.bin_sol is None:
                self.int_feasible = False
            else:
                self.int_feasible = max(self.bin_sol % 1) == 0


        def print_node(self):
            print(self.x, self.ub, self.bin_sol, self.int_feasible)


    def __init__(self, mps_path, branching_rule, sb_score_fn = 'product', node_selection="best-bound", 
                 collect_leaf_nodes=False, collect_tree_sizes=False, tree_estimate_fn='exponential', presolve = False):

        self.mps_path = mps_path
        self.nodes_limit: int = 10**7
        self.grb_model = self.GRBModel(mps_path, presolve)
        self.branching_stats = self.Stats(self.grb_model.n)
        self.node_selection = node_selection
        if node_selection == "best-bound":
            self.add_nodes = self.add_best_bound_first_nodes
        elif node_selection == "depth-first":
            self.add_nodes = self.add_depth_first_search_node
        else:
            sys.exit("node selection rule not recognized")

        self.branching_decision = BranchingRules(
            branching_rule, sb_score_fn, self.grb_model.n, self.grb_model, self.opt_tree, tree_estimate_fn
        )

        self.collect_leaf_nodes = collect_leaf_nodes
        self.collect_tree_sizes = collect_tree_sizes
        if collect_tree_sizes: self.tree_size_info = np.zeros((2*self.nodes_limit+1, 5), int) # child1, child2, treesize, 0treesize, 1treesize
        if collect_leaf_nodes: self.leaf_nodes = []


    def add_best_bound_first_nodes(self, children):

        for child_node in children:
            bisect.insort(self.remaining_nodes, child_node, key=attrgetter('ub'))  # else add to open nodes

        return

    def add_depth_first_search_node(self, children):

        if len(children) == 1:
            self.remaining_nodes.append(children[0])

        elif children[0].ub >= children[1].ub:
                self.remaining_nodes.extend(children)
        else:
            self.remaining_nodes.extend([children[1], children[0]])

        return

    def solve_bnb(self):
        
        for x in self.grb_model.bin_var:
            x.vtype = GRB.CONTINUOUS
        self.grb_model.model.update()

        root = self.Node(2 * np.ones(self.grb_model.n).astype(np.int8), self.grb_model)

        if root.bin_sol is None or root.int_feasible:
            self.remaining_nodes = []
        else:
            self.remaining_nodes = [root]

        self.branching_decision.root_lp_gap = root.ub - self.branching_decision.ip_val

        while self.remaining_nodes and self.branching_stats.branching_count < self.nodes_limit:
            curr_node = self.remaining_nodes.pop()
            self.branch(curr_node)

        for x in self.grb_model.bin_var:
            x.vtype = GRB.BINARY
        self.grb_model.model.update()

        if self.collect_tree_sizes:
            for row_num in range(2*self.branching_stats.branching_count, -1, -1):
                row = self.tree_size_info[row_num, :]
                if row[2] == 0:
                    row[3] = self.tree_size_info[row[0], 2]
                    row[4] = self.tree_size_info[row[1], 2]

                    if (row[3] > 0 and row[4] > 0) or self.node_selection == "best-bound":
                        row[2] = row[3:5].sum() + 1

            completed_subtrees = self.tree_size_info[self.tree_size_info[:, 2] > 1]
            self.expected_asymmetry = np.sum(completed_subtrees[:, 3])/np.sum(completed_subtrees[:, 4])

        if self.remaining_nodes and self.branching_stats.branching_count >= self.nodes_limit:
            self.branching_stats.dual_bound = self.remaining_nodes[-1].ub
            return self.branching_stats.branching_count, \
                   self.branching_stats.dual_bound * self.grb_model.changed_sense, \
                   (root.ub - self.branching_stats.dual_bound) / (root.ub - self.branching_stats.known_opt)
        else:
            # either (non-degenerate) self.branching_stats.primal_bound = known_opt
            # or (dual degenerate) curr_node.ub = known_opt
            # assert(min(abs(self.branching_stats.known_opt - self.branching_stats.primal_bound), abs(curr_node.ub - self.branching_stats.known_opt)) < 1e-5)

            if not(root.int_feasible or abs((self.branching_stats.dual_bound - self.branching_stats.known_opt)/self.branching_stats.known_opt) < 1e-4):
                print(self.mps_path, self.branching_stats.dual_bound, self.branching_stats.known_opt)
            return self.branching_stats.branching_count, \
                   self.branching_stats.dual_bound * self.grb_model.changed_sense, \
                   1.0


    def branch(self, node):

        branch_on, _ = self.branching_decision.choose_branching_var(node)
        self.add_children_nodes(node, branch_on)

        self.branching_stats.branching_count += 1

        if node.bin_sol[branch_on] % 1 == 0:
            self.branching_stats.int_branching_count += 1

        return branch_on



    def add_children_nodes(self, node, branch_on):

        child_bounds: [float, float] = [None, None]
        open_children = []
        
        for val in [0, 1]:
            new_face = node.x.copy()
            new_face[branch_on] = val

            child_node = self.Node(new_face, self.grb_model)
            child_node.id = (2*self.branching_stats.branching_count) + 1 + val

            if self.branching_decision.update_pc:
                if child_node.ub > -float('inf'):
                    self.branching_decision.pseudo_costs[
                        val, branch_on, self.branching_decision.data_counter[val, branch_on]] = \
                            (node.ub - child_node.ub) / abs(val - node.bin_sol[branch_on])
                    self.branching_decision.data_counter[val, branch_on] += 1
                    self.branching_decision.reliability_counter[val, branch_on] += 1

                elif self.branching_decision.rbpc_include_inf:
                    self.branching_decision.pseudo_costs[
                        val, branch_on, self.branching_decision.data_counter[val, branch_on]] = float('inf')
                    self.branching_decision.data_counter[val, branch_on] += 1

            child_bounds[val] = child_node.ub

            if not child_node.int_feasible and child_node.ub > max(self.branching_stats.primal_bound, self.branching_stats.known_opt):
                open_children.append(child_node)

            else: # prune
                if child_node.ub > self.branching_stats.dual_bound: # update dual bound
                    self.branching_stats.dual_bound = child_node.ub

                if child_node.int_feasible and child_node.ub > self.branching_stats.primal_bound: # update primal
                    self.branching_stats.primal_bound = child_node.ub

                    # update primal bound for Eff-SB
                    if self.branching_stats.primal_bound > self.branching_decision.ip_val:
                        self.branching_decision.ip_val = self.branching_stats.primal_bound

                    # prune nodes with lesser bound
                    cut_off = bisect.bisect_left(self.remaining_nodes, child_node.ub, key=attrgetter("ub"))
                    del self.remaining_nodes[:cut_off]
                
                if self.collect_leaf_nodes:
                    self.leaf_nodes.append(child_node.x)

                if self.collect_tree_sizes:
                    self.tree_size_info[child_node.id, 2] = 1

        if open_children != []: self.add_nodes(open_children)
        if self.collect_tree_sizes: self.tree_size_info[node.id, :2] =  (child_node.id - 1, child_node.id)
        return child_bounds
