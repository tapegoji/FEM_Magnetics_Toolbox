# Python standard libraries
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

# Local libraries
import femmt.Functions as ff
from femmt.Enumerations import *

class Conductor:
    """
    A winding defines a conductor which is wound around a magnetic component such as transformer or inductance.
    The winding is defined by its conductor and the way it is placed in the magnetic component. To allow different
    arrangements of the conductors in several winding windows (hexagonal or square packing, interleaved, ...) in
    this class only the conductor parameters are specified. 

    TODO More documentation
    """

    conductor_type: ConductorType
    conductor_arrangement: ConductorArrangement = None
    wrap_para: WrapParaType = None
    conductor_radius: float = None
    winding_number: int
    thickness: float = None
    ff: float = None
    strand_radius: float = None
    n_strands: int = 0
    n_layers: int
    a_cell: float
    cond_sigma: float
    parallel: int = 1 # TODO What is this parameter?

    conductor_is_set: bool

    # Not used in femmt_classes. Only needed for to_dict()
    conductivity: Conductivity = None

    def __init__(self, winding_number: int, conductivity: float):
        if winding_number < 0:
            raise Exception("Winding index cannot be negative.")

        self.winding_number = winding_number
        self.conductivity = conductivity
        self.conductor_is_set = False

        dict_material_database = ff.wire_material_database()
        if conductivity.name in dict_material_database:
            self.cond_sigma = dict_material_database[conductivity.name]["sigma"]
        else:
            raise Exception(f"Material {conductivity.name} not found in database")

    def set_rectangular_conductor(self, thickness: float):
        if self.conductor_is_set:
            raise Exception("Only one conductor can be set for each winding!")

        self.conductor_is_set = True
        self.conductor_type = ConductorType.RectangularSolid
        self.thickness = thickness
        self.a_cell = 1 # TODO Surface size needed?
        self.conductor_radius = 1 # Revisit

    def set_solid_round_conductor(self, conductor_radius: float, conductor_arrangement: ConductorArrangement):
        if self.conductor_is_set:
            raise Exception("Only one conductor can be set for each winding!")

        self.conductor_is_set = True
        self.conductor_type = ConductorType.RoundSolid
        self.conductor_arrangement = conductor_arrangement
        self.conductor_radius = conductor_radius
        self.a_cell = np.pi * conductor_radius ** 2

    def set_litz_round_conductor(self, conductor_radius: float, number_strands: int, strand_radius: float, fill_factor: float, conductor_arrangement: ConductorArrangement):
        """
        Only 3 of the 4 parameters are needed. The other one needs to be none
        """
        if self.conductor_is_set:
            raise Exception("Only one conductor can be set for each winding!")

        self.conductor_is_set = True
        self.conductor_type = ConductorType.RoundLitz
        self.conductor_arrangement = conductor_arrangement
        self.conductor_radius = conductor_radius
        self.n_strands = number_strands
        self.strand_radius = strand_radius
        self.ff = fill_factor

        if number_strands is None:
            self.n_strands = conductor_radius ** 2 / strand_radius ** 2 * fill_factor
        elif conductor_radius is None:
            self.conductor_radius = np.sqrt(number_strands * strand_radius ** 2 / fill_factor)
        elif fill_factor is None:
            ff_exact = number_strands * strand_radius ** 2 / conductor_radius ** 2
            self.ff = np.around(ff_exact, decimals=2)
        elif strand_radius is None:
            self.strand_radius = np.sqrt(conductor_radius**2*fill_factor/number_strands)
        else:
            raise Exception("1 of the 4 parameters need to be None.")

        self.n_layers = ff.NbrLayers(number_strands)
        self.a_cell = self.n_strands * self.strand_radius ** 2 * np.pi / self.ff

        ff.femmt_print(f"Updated Litz Configuration: \n"
              f" ff: {self.ff} \n"
              f" Number of layers/strands: {self.n_layers}/{self.n_strands} \n"
              f" Strand radius: {self.strand_radius} \n"
              f" Conductor radius: {self.conductor_radius}\n"
              f"---")

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    
    def __ne__(self, other):
        return self.__dict__ != other.__dict__

    def to_dict(self):
        return {
            "winding_number": self.winding_number,
            "conductivity": self.conductivity.name,
            "conductor_type": self.conductor_type.name,
            "thickness": self.thickness,
            "conductor_radius": self.conductor_radius,
            "conductor_arrangement": self.conductor_arrangement.name if self.conductor_arrangement is not None else None,
            "number_strands": self.n_strands,
            "strand_radius": self.strand_radius,
            "fill_factor": self.ff
        }

class Core:
    """
    This creates the core base for the model.

    frequency = 0: mu_rel only used if non_linear == False
    frequency > 0: mu_rel is used
    
    TODO More Documentation
    """
    type: str

    # Standard material data
    material: str  # "95_100" := TDK-N95 | Currently only works with Numbers corresponding to BH.pro

    # Permeability
    # TDK N95 as standard material:
    permeability_type: PermeabilityType
    mu_rel: float           # Relative Permeability [if complex: mu_complex = re_mu_rel + j*im_mu_rel with mu_rel=|mu_complex|]
    phi_mu_deg: float       # mu_complex = mu_rel * exp(j*phi_mu_deg)
    # re_mu_rel: float      # Real part of relative Core Permeability  [B-Field and frequency-dependent]
    # im_mu_rel: float      # Imaginary part of relative Core Permeability

    # Permitivity - [Conductivity in a magneto-quasistatic sense]
    sigma: float            # Imaginary part of complex equivalent permittivity [frequency-dependent]

    # Dimensions
    core_w: float           # Axi symmetric case | core_w := 2x core radius
    core_h: float
    window_w: float         # Winding window width
    window_h: float         # Winding window height
    core_type: str = "EI"   # Basic shape of magnetic conductor
    
    steinmetz_loss: int = 0
    generalized_steinmetz_loss: int = 0
    
    # TODO Does this represent the number of windows the EI core has?
    number_core_windows: int

    # Needed for to_dict
    loss_approach: LossApproach = None

    # TODO explanation
    r_inner: float
    r_outer: float

    correct_outer_leg: bool

    def __init__(self, core_w: float, window_w: float, window_h: float, material: str = "custom",  # "95_100" 
                   loss_approach: LossApproach = LossApproach.LossAngle, mu_rel: float = 3000,
                   phi_mu_deg: float = None, sigma: float = None, non_linear: bool = False, correct_outer_leg: bool = False, **kwargs):
        # Set parameters
        self.core_w = core_w
        self.core_h = None  # TODO Set core_h to not none
        self.window_w = window_w
        self.window_h = window_h
        self.type = "axi_symmetric"
        self.material = material
        self.non_linear = non_linear
        self.mu_rel = mu_rel
        self.phi_mu_deg = phi_mu_deg

        self.loss_approach = loss_approach

        self.number_core_windows = 2
        self.correct_outer_leg = correct_outer_leg

        self.r_inner = window_w + core_w / 2
        if correct_outer_leg:
            A_out = 200 * 10 ** -6
            self.r_outer = np.sqrt(A_out / np.pi + self.r_inner ** 2)  # Hardcode for PQ 40/40
        else:
            self.r_outer = np.sqrt((core_w / 2) ** 2 + self.r_inner ** 2)

        # Check loss approach
        if loss_approach == LossApproach.Steinmetz:
            self.sigma = 0
            if self.material != "custom":
                self.permeability_type = PermeabilityType.FromData
                self.sigma = f"sigma_from_{self.material}"
            else:
                raise Exception(f"When steinmetz losses are set a material needs to be set as well.")
        elif loss_approach == LossApproach.LossAngle:
            if self.material == "custom":
                self.sigma = sigma
            else:
                self.sigma = f"sigma_from_{self.material}"

            if phi_mu_deg is not None and phi_mu_deg != 0:
                self.permeability_type = PermeabilityType.FixedLossAngle
            else:
                self.permeability_type = PermeabilityType.RealValue
        else:
            raise Exception("Loss approach {loss_approach.value} is not implemented")

        # Set attributes of core with given keywords
        # TODO Should we allow this? Technically this is not how an user interface should be designed
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Needed because of to_dict
        self.kwargs = kwargs

    def to_dict(self):
        return {
            "core_w": self.core_w,
            "window_w": self.window_w,
            "window_h": self.window_h,
            "material": self.material,
            "loss_approach": self.loss_approach.name,
            "mu_rel": self.mu_rel,
            "phi_mu_deg": self.phi_mu_deg,
            "sigma": self.sigma,
            "non_linear": self.non_linear,
            "correct_outer_leg": self.correct_outer_leg
        }

class AirGaps:
    """
    Contains methods and arguments to describe the air gaps in a magnetic component

    An air gap can be added with the add_air_gap function. It is possible to set different positions and heights.
    """

    core: Core
    midpoints: List[List[float]]  #: list: [position_tag, air_gap_position, air_gap_h]
    number: int

    # Needed for to_dict
    air_gap_settings: List

    def __init__(self, method: AirGapMethod, core: Core):
        self.method = method
        self.core = core
        self.midpoints = []
        self.number = 0
        self.air_gap_settings = []

    def add_air_gap(self, leg_position: AirGapLegPosition, height: float, position_value: Optional[float] = 0):
        """
        Brings a single air gap to the core.

        :param leg_posistion: CenterLeg, OuterLeg
        :type leg_position: AirGapLegPosition
        :param position_value: if AirGapMethod == Percent: 0...100, elif AirGapMethod == Manually: position hight in [m]
        :type position_value: float
        :param height: Air gap height in [m]
        :type height: float
        """
        self.air_gap_settings.append({
            "leg_position": leg_position.name, 
            "position_value": position_value,
            "height": height})

        for index, midpoint in enumerate(self.midpoints):
            if midpoint[0] == leg_position and midpoint[1] + midpoint[2] < position_value - height \
                    and midpoint[1] - midpoint[2] > position_value + height:
                raise Exception(f"Air gaps {index} and {len(self.midpoints)} are overlapping")

        if leg_position == AirGapLegPosition.LeftLeg or leg_position == AirGapLegPosition.RightLeg:
            raise Exception("Currently the legpositions LeftLeg and RightLeg are not supported")

        if self.method == AirGapMethod.Center:
            if self.number >= 1:
                raise Exception("The 'center' position for air gaps can only have 1 air gap maximum")
            else:
                self.midpoints.append([0, 0, height])
                self.number += 1
                
        elif self.method == AirGapMethod.Manually:
            self.midpoints.append([leg_position.value, position_value, height])
            self.number += 1
        elif self.method == AirGapMethod.Percent:
            if position_value > 100 or position_value < 0:
                raise Exception("AirGap position values for the percent method need to be between 0 and 100.")
            position = position_value / 100 * self.core.window_h - self.core.window_h / 2

            # When the position is above the winding window it needs to be adjusted
            if position + height / 2 > self.core.window_h / 2:
                position -= (position + height / 2) - self.core.window_h / 2
            elif position - height / 2 < -self.core.window_h / 2:
                position += -self.core.window_h / 2 - (position - height / 2) 

            self.midpoints.append([leg_position.value, position, height])
            self.number += 1
        else:
            raise Exception(f"Method {self.method} is not supported.")

    def to_dict(self):
        if self.number == 0:
            return {}

        content = {
            "method": self.method.name,
            "air_gap_number": len(self.air_gap_settings)
        }

        if self.number > 0:
            content["air_gaps"] = self.air_gap_settings

        return content

class Insulation:
    """
    This class defines insulation for the model.
    An insulation between the winding window and the core can always be set.
    When having a inductor only the primary2primary insulation is necessary.
    When having a (integrated) transformer secondary2secondary and primary2secondary insulations can be set as well.
    """
    inner_winding_insulations: List[float]
    vww_insulation: float
    core_cond: List[float]

    insulation_delta: float

    def __init__(self):
        # Default value for all insulations
        # If the gaps between insulations and core (or windings) are to big/small just change this value
        self.insulation_delta = 0.00001
        self.vww_insulation = None

    def add_winding_insulations(self, inner_winding_insulations, virtual_winding_window_insulation = None):
        if inner_winding_insulations is []:
            raise Exception("Inner winding insulations list cannot be empty.")
        if virtual_winding_window_insulation is None:
            virtual_winding_window_insulation = 0

        self.inner_winding_insulations = inner_winding_insulations
        self.vww_insulation = virtual_winding_window_insulation

    def add_core_insulations(self, top_core, bot_core, left_core, right_core):
        if top_core is None:
            top_core = 0
        if bot_core is None:
            bot_core = 0
        if left_core is None:
            left_core = 0
        if right_core is None:
            right_core = 0

        self.core_cond = [top_core, bot_core, left_core, right_core]

    def to_dict(self):
        if len(self.inner_winding_insulations) == 0 and self.vww_insulation is None:
            return {}

        return {
            "inner_winding_insulations": self.inner_winding_insulations,
            "core_insulations": self.core_cond,
            "vww_insulation": self.vww_insulation
        }

@dataclass
class StrayPath:
    """
    This class is needed when an integrated transformer shall be created.

    TODO: Thickness of the stray path must be fitted for the real Tablet (effective area of the
    "stray air gap" is different in axi-symmetric approximation
    """

    start_index: int        # Air gaps are sorted from lowest to highest. This index refers to the air_gap index bottom up
    length: float           # Resembles the length of the whole tablet starting from the y-axis

class VirtualWindingWindow:
    """
    A virtual winding window is the area, where either some kind of interleaved conductors or a one winding
    (primary, secondary,...) is placed in a certain way.

    An instance of this class will be automatically created when the Winding is added to the MagneticComponent
    """

    # Rectangular frame:
    bot_bound: float
    top_bound: float
    left_bound: float
    right_bound: float

    winding_type: WindingType
    winding_scheme: WindingScheme # Or InterleavedWindingScheme in case of an interleaved winding
    wrap_para: WrapParaType

    windings: List[Conductor]
    turns: List[int]

    winding_is_set: bool
    winding_insulation: float

    def __init__(self, bot_bound: float, top_bound: float, left_bound: float, right_bound: float):
        self.bot_bound = bot_bound
        self.top_bound = top_bound
        self.left_bound = left_bound
        self.right_bound = right_bound
        self.winding_is_set = False

    def set_winding(self, conductor: Conductor, turns: int, winding_scheme: WindingScheme, wrap_para_type: WrapParaType = None):
        self.winding_type = WindingType.Single
        self.winding_scheme = winding_scheme
        self.windings = [conductor]
        self.turns = [turns]
        self.winding_is_set = True
        self.wrap_para = wrap_para_type

        if winding_scheme is WindingScheme.FoilVertical and wrap_para_type is None:
            raise Exception("When winding scheme is FoilVertical a wrap para type must be set.")

    def set_interleaved_winding(self, conductor1: Conductor, turns1: int, conductor2: Conductor, turns2: int, winding_scheme: InterleavedWindingScheme, winding_insulation: float):
        self.winding_type = WindingType.Interleaved
        self.winding_scheme = winding_scheme
        self.windings = [conductor1, conductor2]
        self.turns = [turns1, turns2]
        self.winding_is_set = True
        self.winding_insulation = winding_insulation
        self.wrap_para = None

    def __repr__(self):
        return f"WindingType: {self.winding_type}, WindingScheme: {self.winding_scheme}, Bounds: bot: {self.bot_bound}, top: {self.top_bound}, left: {self.left_bound}, right: {self.right_bound}"

    def to_dict(self):
        return {
            "bot_bound": self.bot_bound,
            "top_bound": self.top_bound,
            "left_bound": self.left_bound,
            "right_bound": self.right_bound,
            "winding_type": self.winding_type.name,
            "winding_scheme": self.winding_scheme.name if self.winding_scheme is not None else None,
            "wrap_para": self.wrap_para.name if self.wrap_para is not None else None,
            "windings": [winding.to_dict() for winding in self.windings],
            "turns": self.turns
        }

    # TODO Since in combine_vww it is necessary to compare vwws maybe a __eq__ and __ne__ 
    # function should be implemented.

class WindingWindow:
    max_bot_bound: float
    max_top_bound: float
    max_left_bound: float
    max_right_bound: float
    
    # 4 different insulations which can be Null if there is a vww overlapping
    # The lists contain 4 values x1, y1, x2, y2 where (x1, y1) is the lower left and (x2, y2) the upper right point 
    top_iso: List[float]
    left_iso: List[float]
    bot_iso: List[float]
    right_iso: List[float]

    vww_insulations: float
    insulations: Insulation
    split_type: WindingWindowSplit
    stray_path: StrayPath
    air_gaps: AirGaps

    horizontal_split_factor: float
    vertical_split_factor: float

    virtual_winding_windows: List[VirtualWindingWindow]

    def __init__(self, core: Core, insulations: Insulation, stray_path: StrayPath = None, air_gaps: AirGaps = None):
        self.max_bot_bound = -core.window_h / 2 + insulations.core_cond[0]
        self.max_top_bound = core.window_h / 2 - insulations.core_cond[1]
        self.max_left_bound = core.core_w / 2 + insulations.core_cond[2]
        self.max_right_bound = core.r_inner - insulations.core_cond[3]

        # Insulations between vwws
        self.vww_insulations = insulations.vww_insulation
        self.insulations = insulations

        self.stray_path = stray_path
        self.air_gaps = air_gaps

    def split_window(self, split_type: WindingWindowSplit, horizontal_split_factor: float = 0.5, vertical_split_factor: float = 0.5):
        self.split_type = split_type

        self.horizontal_split_factor = horizontal_split_factor
        self.vertical_split_factor = vertical_split_factor

        # Calculate split lengths
        if self.stray_path is not None and self.air_gaps is not None and self.air_gaps.number > self.stray_path.start_index:
            air_gap_1_position = self.air_gaps.midpoints[self.stray_path.start_index][1]
            air_gap_2_position = self.air_gaps.midpoints[self.stray_path.start_index+1][1]
            max_pos = max(air_gap_2_position, air_gap_1_position)
            min_pos = min(air_gap_2_position, air_gap_1_position) 
            distance = max_pos - min_pos 
            horizontal_split = min_pos + distance / 2
            vertical_split = self.max_left_bound + (self.max_right_bound - self.max_left_bound) * vertical_split_factor
            self.vww_insulations = distance
        else:
            horizontal_split = self.max_top_bound - abs(self.max_bot_bound - self.max_top_bound) * horizontal_split_factor
            vertical_split = self.max_left_bound + (self.max_right_bound - self.max_left_bound) * vertical_split_factor

        # Check for every possible split type and return the corresponding VirtualWindingWindows
        if split_type == WindingWindowSplit.NoSplit:
            complete = VirtualWindingWindow(
                bot_bound = self.max_bot_bound,
                top_bound = self.max_top_bound,
                left_bound = self.max_left_bound,
                right_bound = self.max_right_bound)

            self.virtual_winding_windows = [complete]
            return complete
        elif split_type == WindingWindowSplit.VerticalSplit:
            right = VirtualWindingWindow(
                bot_bound = self.max_bot_bound,
                top_bound = self.max_top_bound,
                left_bound = vertical_split + self.vww_insulations / 2,
                right_bound = self.max_right_bound)

            left = VirtualWindingWindow(
                bot_bound = self.max_bot_bound,
                top_bound = self.max_top_bound,
                left_bound = self.max_left_bound,
                right_bound = vertical_split - self.vww_insulations / 2)

            self.virtual_winding_windows = [left, right]
            return left, right
        elif split_type == WindingWindowSplit.HorizontalSplit:
            top = VirtualWindingWindow(
                bot_bound = horizontal_split + self.vww_insulations / 2,
                top_bound = self.max_top_bound,
                left_bound = self.max_left_bound,
                right_bound = self.max_right_bound)

            bot = VirtualWindingWindow(
                bot_bound = self.max_bot_bound,
                top_bound = horizontal_split - self.vww_insulations / 2,
                left_bound = self.max_left_bound,
                right_bound = self.max_right_bound)

            self.virtual_winding_windows = [top, bot]
            return top, bot
        elif split_type == WindingWindowSplit.HorizontalAndVerticalSplit:
            top_left = VirtualWindingWindow(
                bot_bound = horizontal_split + self.vww_insulations / 2,
                top_bound = self.max_top_bound,
                left_bound = self.max_left_bound,
                right_bound = vertical_split - self.vww_insulations / 2)

            top_right = VirtualWindingWindow(
                bot_bound = horizontal_split + self.vww_insulations / 2,
                top_bound = self.max_top_bound,
                left_bound = vertical_split + self.vww_insulations / 2,
                right_bound = self.max_right_bound)

            bot_left = VirtualWindingWindow(
                bot_bound = self.max_bot_bound,
                top_bound = horizontal_split - self.vww_insulations / 2,
                left_bound = self.max_left_bound,
                right_bound = vertical_split - self.vww_insulations / 2)

            bot_right = VirtualWindingWindow(
                bot_bound = self.max_bot_bound,
                top_bound = horizontal_split - self.vww_insulations / 2,
                left_bound = vertical_split + self.vww_insulations / 2,
                right_bound = self.max_right_bound)

            self.virtual_winding_windows = [top_left, top_right, bot_left, bot_right]
            return top_left, top_right, bot_left, bot_right
        else:
            raise Exception(f"Winding window split type {split_type} not found")

    def combine_vww(self, vww1, vww2):
        index1 = self.virtual_winding_windows.index(vww1)
        index2 = self.virtual_winding_windows.index(vww2)

        if abs(index2-index1) == 3:
            raise Exception("Cannot combine top left and bottom right.")
        # TODO add check for top right and bottom left

        self.virtual_winding_windows.remove(vww1)
        self.virtual_winding_windows.remove(vww2)

        new_vww = VirtualWindingWindow(bot_bound = min(vww1.bot_bound, vww2.bot_bound), 
                                    top_bound = max(vww1.top_bound, vww2.top_bound), 
                                    left_bound = min(vww1.left_bound, vww2.left_bound), 
                                    right_bound = max(vww1.right_bound, vww2.right_bound))

        self.virtual_winding_windows.append(new_vww)

        return new_vww