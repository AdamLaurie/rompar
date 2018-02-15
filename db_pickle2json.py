from rompar import *
import rompar

# For reference
def save_grid_pickle(self, fn=None):
    if not fn:
        fn = self.basename + '_s%d.grid' % self.saven
    symlinka(fn, self.basename + '.grid')
    gridout = open(fn, 'wb')
    pickle.dump((self.grid_intersections, self.Data, self.grid_points_x, self.grid_points_y, self.config), gridout)
    print 'Saved %s' % fn

'''
def load_grid(self, grid_file=None, apickle=None, gui=True):
    self.gui = gui
    if not apickle:
        with open(grid_file, 'rb') as gridfile:
            apickle = pickle.load(gridfile)
    self.grid_intersections, data, self.grid_points_x, self.grid_points_y, self.config = apickle
...
'''

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert old DB format to new')
    parser.add_argument('pickle', help='Input pickle file')
    parser.add_argument('json', help='Output json file')
    args = parser.parse_args()

    self = rompar.Rompar()

    with open(args.pickle, 'rb') as gridfile:
        apickle = pickle.load(gridfile)
    grid_intersections, data, grid_points_x, grid_points_y, config = apickle

    configj = dict(config.__dict__)
    configj['view'] = configj['view'].__dict__

    j = {
        'grid_intersections': grid_intersections,
        'data': data,
        'grid_points_x': grid_points_x,
        'grid_points_y': grid_points_y,
        'fn': config,
        #'group_cols': group_cols,
        #'group_rows': group_rows,
        'config': configj,
        }

    rompar.load_grid(self, grid_json=j, gui=False)
    rompar.save_grid(self, fn=args.json)

if __name__ == "__main__":
    main()
