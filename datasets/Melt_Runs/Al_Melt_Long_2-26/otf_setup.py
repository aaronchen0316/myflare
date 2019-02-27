import numpy as np
import sys
import crystals
import otf
import kernels
import gp
import qe_input
import initialize_velocities

# -----------------------------------------------------------------------------
#                         1. set initial positions
# -----------------------------------------------------------------------------

# slab parameters
symbol = 'Al'
alat = 8.092 / 2
unit_cell = np.eye(3) * alat
sc_size = 2
fcc_positions = crystals.fcc_positions(alat)
positions = crystals.get_supercell_positions(sc_size, unit_cell, fcc_positions)
cell = unit_cell * 2

# -----------------------------------------------------------------------------
#            2. set initial velocities and previous positions
# -----------------------------------------------------------------------------

nat = len(positions)
temperature = 300  # in kelvin
mass = 27  # in amu

velocities = \
    initialize_velocities.get_random_velocities(nat, temperature, mass)

dt = 0.001  # in ps
previous_positions = positions - velocities * dt


# -----------------------------------------------------------------------------
#                     3. create gaussian process model
# -----------------------------------------------------------------------------

kernel = kernels.two_plus_three_body
kernel_grad = kernels.two_plus_three_body_grad
hyps = np.array([0.1, 1., 0.001, 1, 0.06])
cutoffs = np.array([5.4, 4.5])
hyp_labels = ['sig2', 'ls2', 'sig3', 'ls3', 'noise']
opt_algorithm = 'BFGS'

gp_model = gp.GaussianProcess(kernel, kernel_grad, hyps, cutoffs, hyp_labels,
                              opt_algorithm)


# -----------------------------------------------------------------------------
#                 4. make qe input file for initial structure
# -----------------------------------------------------------------------------

# setup qe file
calculation = 'scf'
input_file_name = 'melt.in'
output_file_name = 'pwscf.out'
pw_loc = '/n/home03/jonpvandermause/qe-6.2.1/bin/pw.x'
pseudo_dir = '/n/home03/jonpvandermause/qe-6.2.1/pseudo'
outdir = './output'
nat = len(positions)
ntyp = 1
species = ['Al'] * nat
ion_names = ['Al']
ion_masses = [mass]
ion_pseudo = ['Al.pbe-n-kjpaw_psl.1.0.0.UPF']
kvec = np.array([2, 2, 2])
ecutwfc = 29  # minimum recommended
ecutrho = 143  # minimum recommended

scf_inputs = dict(pseudo_dir=pseudo_dir,
                  outdir=outdir,
                  nat=nat,
                  ntyp=ntyp,
                  ecutwfc=ecutwfc,
                  ecutrho=ecutrho,
                  cell=cell,
                  species=species,
                  positions=positions,
                  kvec=kvec,
                  ion_names=ion_names,
                  ion_masses=ion_masses,
                  ion_pseudo=ion_pseudo)

# make input file
calc = qe_input.QEInput(input_file_name, output_file_name, pw_loc,
                        calculation, scf_inputs, metal=True)


# -----------------------------------------------------------------------------
#                            4. create otf object
# -----------------------------------------------------------------------------

number_of_steps = 100000  # 100 ps
std_tolerance_factor = 1
init_atoms = [0]
melt_step = 10000  # melt at 10 ps
melt_temp = 4000  # melt temp = 4 K

otf_model = otf.OTF(input_file_name, dt, number_of_steps, gp_model,
                    pw_loc, std_tolerance_factor,
                    prev_pos_init=previous_positions, par=True, parsimony=True,
                    init_atoms=init_atoms,
                    quench_step=melt_step,
                    quench_temperature=melt_temp)
