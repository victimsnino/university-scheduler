import cplex
import numpy as np

def _add_constraint(my_model, variables, sense, value):
    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise ("Not valid operation!")

    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = variables, 
                                                                 val = [1.0]*len(variables))], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

def fill_variables(my_model):
    my_model.variables.add( obj = [1, 1, 1], # x1+x2+x3
                            ub = [5, 5, 5], # x[i] <= 5
                            lb = [1, 1, 1], # x[i] >= 1 
                            names = ["x1", "x2", "x3"])

def fill_constraints(my_model):
    _add_constraint(my_model, ['x1', 'x2'], ">=", 7)
    _add_constraint(my_model, ['x2', 'x3'], "<=", 3)

def print_model_output(my_model):
    print()
    
    # solution.get_status() returns an integer code
    print("Solution status = ",     my_model.solution.get_status(), ":", my_model.solution.status[my_model.solution.get_status()])
    if my_model.solution.get_status() == 1:
        print("Array of X = ",          my_model.solution.get_values())
        print("Solution value  = ",     my_model.solution.get_objective_value())

def main():
    my_model = cplex.Cplex()
    my_model.objective.set_sense(my_model.objective.sense.minimize)

    fill_variables(my_model)
    fill_constraints(my_model)

    my_model.solve()

    print_model_output(my_model)

if __name__ == "__main__":
    main()

