from time import sleep

import numpy as np
from bokeh.io import curdoc
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import HoverTool, Select, Slider, Button
from bokeh.layouts import Row, Column

class GameOfLife():
    def __init__(self, state):
        self.rows = len(state)
        self.cols = len(state[0])

        self.PLOT_HEIGHT = 600
        self.PLOT_WIDTH = 600
        self.CELL_HEIGHT = self.PLOT_HEIGHT / self.rows - 40 / self.rows
        self.CELL_WIDTH = self.PLOT_WIDTH / self.cols - 40 / self.cols

    def calculate_neighbors(self, state, row, col):
        total = 0
        for neighbor in [[row - 1, col], [row, col - 1], [row + 1, col], [row, col + 1], [row - 1, col - 1],
                         [row + 1, col - 1], [row - 1, col + 1], [row + 1, col + 1]]:
            try:
                total += state[neighbor[0], neighbor[1]]
            except IndexError:
                pass
        return total

    def single_generation(self, state):
        neighbors_matrix = self.generate_neighbors_matrix(state)
        for row in range(self.rows):
            for col in range(self.cols):
                cell_neighbors = neighbors_matrix[row, col]
                if state[row, col] == 1:
                    if cell_neighbors < 2 or cell_neighbors > 3:
                        state[row, col] = 0
                else:
                    if cell_neighbors == 3:
                        state[row, col] = 1
        return state

    def generate_neighbors_matrix(self, state):
        neighbors_matrix = np.empty_like(state, dtype=int)
        for row in range(self.rows):
            for col in range(self.cols):
                neighbors_matrix[row, col] = self.calculate_neighbors(state, row, col)
        return neighbors_matrix

    def build_data_sources(self, state):
        neighbors_matrix = self.generate_neighbors_matrix(state)

        alive_cell_indices = state.nonzero()
        alive_cell_x = alive_cell_indices[1]
        alive_cell_y = alive_cell_indices[0]

        alive_cell_indices = [(row, col) for row, col in zip(alive_cell_y, alive_cell_x)]

        alive_cell_neighbors = [neighbors_matrix[row][col] for row, col in alive_cell_indices]

        dead_cell_indices = [(row, col) for row in np.arange(0, self.rows, 1) for col in np.arange(0, self.cols, 1)
                             if (row, col) not in alive_cell_indices]
        dead_cell_neighbors = [neighbors_matrix[row][col] for row, col in dead_cell_indices]

        dead_cell_x = np.array([col for row, col in dead_cell_indices])
        dead_cell_y = np.array([row for row, col in dead_cell_indices])

        alive_cell_x = alive_cell_x + 0.5
        alive_cell_y = self.rows - alive_cell_y - 0.5

        dead_cell_x = dead_cell_x + 0.5
        dead_cell_y = self.rows - dead_cell_y - 0.5

        alive_data_source = ColumnDataSource({'x': alive_cell_x, 'y': alive_cell_y, 'neighbors': alive_cell_neighbors,
                                              'color': ['black']*len(alive_cell_indices),
                                              'cell_states': self.get_cell_states(alive_cell_neighbors, True)})
        dead_data_source = ColumnDataSource({'x': dead_cell_x, 'y': dead_cell_y, 'neighbors': dead_cell_neighbors,
                                             'color': ['white']*len(dead_cell_indices),
                                             'cell_states': self.get_cell_states(dead_cell_neighbors, False)})

        return alive_data_source, dead_data_source

    def get_cell_states(self, neighbors, alive):
        ''' return state of cells given their neighbors'''
        cell_states = []
        if alive:
            for neighbor in neighbors:
                if neighbor < 2:
                    cell_states.append('Lonely :(')
                elif neighbor == 2 or neighbor == 3:
                    cell_states.append('Comfortable :)')
                else:
                    cell_states.append('Overcrowded :/')
        else:
            for neighbor in neighbors:
                if neighbor == 3:
                    cell_states.append('REBORN! :D')
                else:
                    cell_states.append('Barren...')
        return cell_states

with open('in.txt') as f:
    generations = int(f.readline())
    state = f.readlines()
    state = np.array([list(line.strip('\n')) for line in state], dtype=int)

game = GameOfLife(state)

### Visualization of game state ###

alive_data_source, dead_data_source = game.build_data_sources(state)

output_dict = {}

for generation_num in range(0, generations + 1):
    output_dict[generation_num] = game.build_data_sources(state)
    state = game.single_generation(state)

hover = HoverTool(tooltips=[('Neighbors', '@neighbors'),
                            ('State', '@cell_states')
                            ])
plot = figure(plot_height=game.PLOT_HEIGHT, plot_width=game.PLOT_WIDTH, x_range=(0, game.cols),
                   y_range=(0, game.rows), x_axis_type=None, y_axis_type=None,
                   toolbar_location='right', title='Press START to begin')
plot.add_tools(hover)

plot.rect('x', 'y', width=game.CELL_WIDTH, height=game.CELL_HEIGHT, height_units='screen', width_units='screen',
          line_color='black', color='color', hover_fill_color='color',
          hover_line_color='black', hover_alpha=0.5, source=dead_data_source)
plot.rect('x', 'y', width=game.CELL_WIDTH, height=game.CELL_HEIGHT, height_units='screen', width_units='screen',
          line_color='black', color='color', hover_fill_color='color',
          hover_line_color='black', hover_alpha=0.5, source=alive_data_source)

generations_slider = Slider(start=0, end=generations, step=1, value=0, title='Generation')
speed_slider = Slider(start=0.1, end=10, step=0.1, value=1, title='Speed')
alive_color_dropdown = Select(options=['black', 'white', 'blue', 'red', 'green', 'brown', 'yellow', 'grey', 'purple', 'pink'],
                              value='black', title='Color of alive cells')
dead_color_dropdown = Select(options=['black', 'white', 'blue', 'red', 'green', 'brown', 'yellow', 'grey', 'purple', 'pink'],
                             value='white', title='Color of dead cells')
start_button = Button(label='START')

class Callbacks():
    def __init__(self):
        self.speed = 1
        self.starting_gen_num = 0

    def generations_slider_callback(self, attr, old, new):
        self.starting_gen_num = generations_slider.value
        plot.title.text = 'Generation ' + str(self.starting_gen_num)

        self.adjust_data(alive_data_source, dead_data_source, output_dict, self.starting_gen_num)

    def alive_dropdown_callback(self, attr, old, new):
        color_choice = alive_color_dropdown.value
        alive_data_source.data['color'] = [color_choice] * len(alive_data_source.data['color'])

    def dead_dropdown_callback(self, attr, old, new):
        color_choice = dead_color_dropdown.value
        dead_data_source.data['color'] = [color_choice] * len(dead_data_source.data['color'])

    def speed_slider_callback(self, attr, old, new):
        self.speed = speed_slider.value

    def start_button_callback(self):
        for generation_num in range(self.starting_gen_num, generations + 1):
            plot.title.text = 'Generation ' + str(generation_num)
            self.adjust_data(alive_data_source, dead_data_source, output_dict, generation_num)
            sleep(1/(2*self.speed))

    def adjust_data(self, alive_data_source, dead_data_source, output_dict, gen_num):
        output_dict[gen_num][0].data['color'] = [alive_data_source.data['color'][0]] * len(output_dict[gen_num][0].data['x'])
        output_dict[gen_num][1].data['color'] = [dead_data_source.data['color'][0]] * len(output_dict[gen_num][1].data['x'])

        alive_data_source.data = output_dict[gen_num][0].data
        dead_data_source.data = output_dict[gen_num][1].data

callbacks = Callbacks()

generations_slider.on_change('value', callbacks.generations_slider_callback)
speed_slider.on_change('value', callbacks.speed_slider_callback)
alive_color_dropdown.on_change('value', callbacks.alive_dropdown_callback)
dead_color_dropdown.on_change('value', callbacks.dead_dropdown_callback)
start_button.on_click(callbacks.start_button_callback)

layout = Row(Column(generations_slider, alive_color_dropdown, dead_color_dropdown, speed_slider, start_button), plot)
curdoc().add_root(layout)
