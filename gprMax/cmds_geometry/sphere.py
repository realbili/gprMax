# Copyright (C) 2015-2023: The University of Edinburgh, United Kingdom
#                 Authors: Craig Warren, Antonis Giannopoulos, and John Hartley
#
# This file is part of gprMax.
#
# gprMax is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gprMax is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gprMax.  If not, see <http://www.gnu.org/licenses/>.

import logging

import numpy as np

from ..cython.geometry_primitives import build_sphere
from ..materials import Material
from .cmds_geometry import UserObjectGeometry

logger = logging.getLogger(__name__)


class Sphere(UserObjectGeometry):
    """Introduces a spherical object with specific parameters into the model.

    Attributes:
        p1: list of the coordinates (x,y,z) of the centre of the sphere.
        r: float of radius of the sphere.
        material_id: string for the material identifier that must correspond 
                        to material that has already been defined.
        material_ids: list of material identifiers in the x, y, z directions.
        averaging: string (y or n) used to switch on and off dielectric smoothing.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hash = '#sphere'

    def create(self, grid, uip):
        try:
            p1 = self.kwargs['p1']
            r = self.kwargs['r']
        except KeyError:
            logger.exception(f'{self.__str__()} please specify a point and a radius.')
            raise

        # Check averaging
        try:
            # Try user-specified averaging
            averagesphere = self.kwargs['averaging'] 
        except KeyError:
            # Otherwise go with the grid default
            averagesphere = grid.averagevolumeobjects

        # Check materials have been specified
        # Isotropic case
        try:
            materialsrequested = [self.kwargs['material_id']]
        except KeyError:
            # Anisotropic case
            try:
                materialsrequested = self.kwargs['material_ids']
            except KeyError:
                logger.exception(f'{self.__str__()} no materials have been specified')
                raise

        # Centre of sphere
        
        p2 = uip.round_to_grid_static_point(p1)
        #xc, yc, zc = uip.round_to_grid(p1)
        xc, yc, zc = uip.discretise_point(p1)
                

        

        # Look up requested materials in existing list of material instances
        materials = [y for x in materialsrequested for y in grid.materials if y.ID == x]

        if len(materials) != len(materialsrequested):
            notfound = [x for x in materialsrequested if x not in materials]
            logger.exception(f'{self.__str__()} material(s) {notfound} do not exist')
            raise ValueError

        # Isotropic case
        if len(materials) == 1:
            averaging = materials[0].averagable and averagesphere
            numID = numIDx = numIDy = numIDz = materials[0].numID

        # Uniaxial anisotropic case
        elif len(materials) == 3:
            averaging = False
            numIDx = materials[0].numID
            numIDy = materials[1].numID
            numIDz = materials[2].numID
            requiredID = materials[0].ID + '+' + materials[1].ID + '+' + materials[2].ID
            averagedmaterial = [x for x in grid.materials if x.ID == requiredID]
            if averagedmaterial:
                numID = averagedmaterial.numID
            else:
                numID = len(grid.materials)
                m = Material(numID, requiredID)
                m.type = 'dielectric-smoothed'
                # Create dielectric-smoothed constituents for material
                m.er = np.mean((materials[0].er, materials[1].er, 
                                materials[2].er), axis=0)
                m.se = np.mean((materials[0].se, materials[1].se, 
                                materials[2].se), axis=0)
                m.mr = np.mean((materials[0].mr, materials[1].mr, 
                                materials[2].mr), axis=0)
                m.sm = np.mean((materials[0].sm, materials[1].sm, 
                                materials[2].sm), axis=0)

                # Append the new material object to the materials list
                grid.materials.append(m)

        build_sphere(xc, yc, zc, r, grid.dx, grid.dy, grid.dz, numID, 
                     numIDx, numIDy, numIDz, averaging, grid.solid, 
                     grid.rigidE, grid.rigidH, grid.ID)

        dielectricsmoothing = 'on' if averaging else 'off'
        logger.info(f"{self.grid_name(grid)}Sphere with centre {p2[0]:g}m, " +
                    f"{p2[1]:g}m, {p2[2]:g}m, radius {r:g}m, of material(s) " +
                    f"{', '.join(materialsrequested)} created, dielectric " +
                    f"smoothing is {dielectricsmoothing}.")
