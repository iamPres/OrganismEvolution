import numpy as np
import uuid
import collections
import time
from copy import deepcopy
import threading


class Organism:
    def __init__(self, origin, dna, cell_limit, energy_decay, replication_cost) -> None:
        self.cell_limit = cell_limit
        self.energy_decay = energy_decay
        self.origin = origin
        self.originCell = Cell(origin[0], origin[1], uuid.uuid1())
        self.originCell.ableToReplicate = [1,0,0,0]
        self.positions = collections.defaultdict(dict)
        self.members = 0
        self.positions[self.originCell.x][self.originCell.y] = self.originCell
        self.previous_energy_matrix = []
        self.dna = dna
        self.replication_cost = 0.5

    def tick(self, ticks, food_energy):
        energies = self.compute_energies(deepcopy(food_energy), ticks)
        updated_positions = deepcopy(self.positions)
        self.compute_cells(updated_positions, energies)

    def compute_cells(self, cells, energies):
        for idx in list(self.positions):
            for idy in list(self.positions[idx]):
                cell = cells[idx][idy]
                newCells = cell.tick(energies[cell.x][cell.y], self.energy_decay, self.replication_cost)
                if not cell.dead and newCells is not None:
                    if len(newCells) > 0:
                        if self.members < self.cell_limit:
                            for newCell in newCells:
                                self.members += 1
                                cells[newCell.x][newCell.y] = newCell
                if cell.dead: 
                    self.members -= 1
                    cells[cell.x].pop(cell.y)
        self.positions = cells

    def compute_energies(self, energy_matrix, ticks):
        if ticks == 0:
            self.previous_energy_matrix = energy_matrix
            return self.previous_energy_matrix
        elif ticks > 0:
            new_energy_matrix = energy_matrix
            if self.members > 0:
                threads = []
                for idx in list(self.previous_energy_matrix):
                    thread = threading.Thread(target=self.distribute_energies, args=[idx, new_energy_matrix])
                    thread.start()
                    threads.append(thread)
                
                for thread in threads:
                    thread.join()

                self.previous_energy_matrix = new_energy_matrix
            else: return energy_matrix
            return new_energy_matrix
    
    def distribute_energies(self, idx, new_energy_matrix):
        for idy in list(self.previous_energy_matrix[idx]):
            cell_energy = self.previous_energy_matrix[idx][idy]
            if idx in self.positions:
                if idy in self.positions[idx]:
                    self.calculate_replication_possibilities(idx, idy, new_energy_matrix)
            
                    peer_energies = [0,0,0,0]
                    self_energy = self.positions[idx][idy].energy

                    if idx+1 in self.positions:
                        if idy+1 in self.positions[idx+1]:
                            peer_energies[0] = self.positions[idx+1][idy+1].energy
                        if idy-1 in self.positions[idx+1]:
                            peer_energies[1] = self.positions[idx+1][idy-1].energy

                    if idx-1 in self.positions:
                        if idy+1 in self.positions[idx-1]:
                            peer_energies[2] = self.positions[idx-1][idy+1].energy
                        if idy-1 in self.positions[idx-1]:
                            peer_energies[3] = self.positions[idx-1][idy-1].energy
                    input = np.concatenate([peer_energies, [self_energy]])
                    distributed_energies = self.dna.compute(input)
                    distributed_energies = np.multiply(distributed_energies, 0.9)
                    self.positions[idx][idy].replication_energy = distributed_energies
                    if idx+1 in new_energy_matrix:
                        if idy+1 in new_energy_matrix[idx+1]:
                            new_energy_matrix[idx+1][idy+1] += cell_energy * distributed_energies[0]
                        if idy-1 in new_energy_matrix[idx+1]:
                            new_energy_matrix[idx+1][idy-1] += cell_energy * distributed_energies[1]
                    if idx-1 in new_energy_matrix:
                        if idy+1 in new_energy_matrix[idx-1]:
                            new_energy_matrix[idx-1][idy+1] += cell_energy * distributed_energies[2]
                        if idy-1 in new_energy_matrix[idx-1]:
                            new_energy_matrix[idx-1][idy-1] += cell_energy * distributed_energies[3]

    def calculate_replication_possibilities(self, x, y, energies):
        self.positions[x][y].ableToReplicate = [0]*4
        if not y+1 in energies[x+1]:
            self.positions[x][y].ableToReplicate[0] = 1
        if not y-1 in energies[x+1]:
            self.positions[x][y].ableToReplicate[1] = 1
        if not y+1 in energies[x-1]:
            self.positions[x][y].ableToReplicate[2] = 1
        if not y-1 in energies[x-1]:
            self.positions[x][y].ableToReplicate[3] = 1

    def sum_energies(self):
        sum = 0
        for idx in list(self.previous_energy_matrix):
            for idy in list(self.previous_energy_matrix[idx]):
                sum += self.previous_energy_matrix[idx][idy]
        return sum
    
    def kill(self):
        for idx in list(self.positions):
            for idy in list(self.positions[idx]):
                self.positions[idx][idy].die()
class Cell:
    def __init__(self, x, y, id) -> None:
        self.x = x
        self.y = y
        self.id = str(id)
        self.energy = 0
        self.dead = False
        self.ableToReplicate = [0,0,0,0]
        self.replication_energy = [0,0,0,0]

    def tick(self, food_energy, energy_decay, replication_cost):
        self.energy = food_energy
        self.energy -= energy_decay
        newCell = None
        if self.energy > 0.9:
            rep_e = np.multiply(self.replication_energy, self.ableToReplicate)
            transferred_energy = self.energy * np.sum(rep_e)
            self.energy -= transferred_energy
            newCell = self.replicate(rep_e, self.energy)
        if self.energy < 0.1:
            self.die()
            self.energy = 0
        return newCell

    def die(self):
        self.dead = True
    
    def replicate(self, rep_e, host_energy):
        xdir = 1
        ydir = 1
        cells = []
        if not self.ableToReplicate == [0,0,0,0]:
            for i in range(len(self.ableToReplicate)):
                # makes reproduction more costly
                if self.ableToReplicate[i] == 1 and (rep_e[i] == 0 or rep_e[i] > 0.4):
                    if i == 0:
                        xdir = 1
                        ydir = 1
                        cells.append(Cell(self.x+xdir, self.y+ydir, uuid.uuid1()))
                    elif i == 1:
                        xdir = 1
                        ydir = -1
                        cells.append(Cell(self.x+xdir, self.y+ydir, uuid.uuid1()))
                    elif i == 2:
                        xdir = -1
                        ydir = 1
                        cells.append(Cell(self.x+xdir, self.y+ydir, uuid.uuid1()))
                    elif i == 3:
                        xdir = -1
                        ydir = -1
                        cells.append(Cell(self.x+xdir, self.y+ydir, uuid.uuid1()))
                    #cells[len(cells)-1].energy = rep_e[i]*host_energy*0
        return cells
