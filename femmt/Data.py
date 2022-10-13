# Python standard libraries
import os
import numpy as np
from typing import List
from scipy.interpolate import interp1d

# Local libraries
from femmt.Enumerations import ConductorType

class FileData:
    """Contains paths to every folder and file needed in femmt.
    """
    def __init__(self, working_directory: str):
        self.update_paths(working_directory)

    def create_folders(self, *args) -> None:
        """Creates folder for every given folder path (if it does not exist).
        """
        for folder in list(args):
            if not os.path.exists(folder):
                os.mkdir(folder)

    def update_paths(self, working_directory: str) -> None:
        """Sets the local path based on the given working directory

        :param working_directory: working directory folder path
        :type working_directory: str
        """
        # Setup folder paths 
        self.working_directory = working_directory
        self.femmt_folder_path = os.path.dirname(__file__)
        self.mesh_folder_path = os.path.join(self.working_directory, "mesh")
        self.electro_magnetic_folder_path = os.path.join(self.femmt_folder_path, "electro_magnetic")
        self.results_folder_path = os.path.join(self.working_directory, "results")
        self.e_m_values_folder_path = os.path.join(self.results_folder_path, "values")
        self.e_m_fields_folder_path = os.path.join(self.results_folder_path, "fields")
        self.e_m_circuit_folder_path = os.path.join(self.results_folder_path, "circuit")
        self.e_m_strands_coefficients_folder_path = os.path.join(self.electro_magnetic_folder_path, "Strands_Coefficients")
        self.femm_folder_path = os.path.join(self.working_directory, "femm")
        self.reluctance_model_folder_path = os.path.join(self.working_directory, "reluctance_model")
        self.thermal_results_folder_path = os.path.join(self.results_folder_path, "thermal")

        # Setup file paths
        self.e_m_results_log_path = os.path.join(self.results_folder_path, "log_electro_magnetic.json")
        self.femm_results_log_path = os.path.join(self.femm_folder_path, "result_log_femm.json")
        self.config_path = os.path.join(self.femmt_folder_path, "config.json")
        self.e_m_mesh_file = os.path.join(self.mesh_folder_path, "electro_magnetic.msh")
        self.model_geo_file = os.path.join(self.mesh_folder_path, "model.geo_unrolled")
        self.hybrid_mesh_file = os.path.join(self.mesh_folder_path, "hybrid.msh")
        self.hybrid_color_mesh_file = os.path.join(self.mesh_folder_path, "hybrid_color.msh")
        self.hybrid_color_visualize_file = os.path.join(self.mesh_folder_path, "hybrid_color.png")
        self.thermal_mesh_file = os.path.join(self.mesh_folder_path, "thermal.msh")

        self.onelab_folder_path = None

        # Create necessary folders
        self.create_folders(self.femmt_folder_path, self.mesh_folder_path, self.electro_magnetic_folder_path, 
            self.results_folder_path, self.e_m_values_folder_path, self.e_m_fields_folder_path, 
            self.e_m_circuit_folder_path, self.e_m_strands_coefficients_folder_path)

class MeshData:
    """Contains data which is needed for the mesh generation.
    Is updated by high_level_geo_gen.
    """

    global_accuracy: float  # Parameter for mesh-accuracy
    padding: float           # > 1
    skin_mesh_factor: float
    c_core : float
    c_window: float
    c_conductor = List[float]
    c_center_conductor = List[float]

    mu0: float
    core_w: float
    window_w: float
    windings: List["Conductor"] # This is written as string because its a forward import

    def __init__(self, global_accuracy: float, padding: float, mu0: float, core_w: float, window_w: float, windings: List["Conductor"]):
        self.global_accuracy = global_accuracy
        self.padding = padding
        self.mu0 = mu0
        self.core_w = core_w
        self.window_w = window_w
        self.windings = windings

        # Empty lists
        self.c_conductor = [None] * len(windings)
        self.c_center_conductor = [None] * len(windings)

    def update_data(self, frequency: float, skin_mesh_factor: float) -> None:
        """Updates the mesh data according to the given frequency and skin_mesh_factor.

        :param frequency: Frequency of the model (updates skin depth which affects the mesh)
        :type frequency: float
        :param skin_mesh_factor: Factor for skin mesh
        :type skin_mesh_factor: float
        """

        # Mesh-Parameters must be updated depending on geometry size
        self.c_core = self.core_w / 10. * self.global_accuracy
        self.c_window = self.window_w / 30 * self.global_accuracy
        self.skin_mesh_factor = skin_mesh_factor

        # Update Skin Depth (needed for meshing)
        if frequency is not None:
            if frequency == 0:
                self.delta = 1e9
            else:
                self.delta = np.sqrt(2 / (2 * frequency * np.pi * self.windings[0].cond_sigma * self.mu0))
            for i in range(len(self.windings)):
                if self.windings[i].conductor_type == ConductorType.RoundSolid:
                    self.c_conductor[i] = min([self.delta * self.skin_mesh_factor, self.windings[i].conductor_radius / 4 * self.global_accuracy]) #* self.mesh.skin_mesh_factor])
                    self.c_center_conductor[i] = self.windings[i].conductor_radius / 4 * self.global_accuracy  # * self.mesh.skin_mesh_factor
                elif self.windings[i].conductor_type == ConductorType.RoundLitz:
                    self.c_conductor[i] = self.windings[i].conductor_radius / 4 * self.global_accuracy
                    self.c_center_conductor[i] = self.windings[i].conductor_radius / 4 * self.global_accuracy
                else:
                    self.c_conductor[i] = 0.0001  # TODO: dynamic implementation

class AnalyticalCoreData:
    # TODO Documentation
    
    e_phi_100000 = 37
    e_r_100000 = 1.3969e+05


    e_phi_200000 = 30
    e_r_200000 = 1.1663e+05


    e_phi_300000 = 27
    e_r_300000 = 1.0158e+05

    def imag_deg(amp, phi_deg):
        return amp * np.sin(phi_deg / 180 * np.pi)


    def f_N95_er_imag(f):
        if f < 100000:
            return AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_100000, AnalyticalCoreData.e_phi_100000)
        if f > 300000:
            return AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_300000, AnalyticalCoreData.e_phi_300000)
        else:
            if f >= 200000:
                return AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_200000, AnalyticalCoreData.e_phi_200000) + \
                    (AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_300000, AnalyticalCoreData.e_phi_300000) - \
                        AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_200000, AnalyticalCoreData.e_phi_200000)) / 100000 * (f - 200000)
            if f < 200000:
                return AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_100000, AnalyticalCoreData.e_phi_100000) + \
                    (AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_200000, AnalyticalCoreData.e_phi_200000) - \
                        AnalyticalCoreData.imag_deg(AnalyticalCoreData.e_r_100000, AnalyticalCoreData.e_phi_100000)) / 100000 * (f - 100000)


    # --------------------------------------------------------------------------------------------------------
    N95_b_200000 = [
        0.000000000000000000e+00, 2.144700000000000079e-02, 2.150099999999999928e-02, 2.132799999999999974e-02,
        2.081399999999999917e-02, 2.086700000000000013e-02, 2.117199999999999985e-02, 2.058300000000000060e-02,
        2.030399999999999913e-02, 2.091600000000000056e-02, 2.454999999999999891e-02, 2.633299999999999877e-02,
        2.176700000000000162e-02, 2.197400000000000048e-02, 2.276900000000000104e-02, 2.588700000000000029e-02,
        3.192699999999999705e-02, 3.809699999999999892e-02, 5.890000000000000097e-02, 6.658100000000000129e-02,
        6.677299999999999902e-02, 6.954200000000000659e-02, 7.366899999999999837e-02, 7.554700000000000304e-02,
        8.095199999999999618e-02, 8.383699999999999486e-02, 9.049300000000000399e-02, 9.800999999999999990e-02,
        1.040399999999999936e-01, 1.079299999999999982e-01, 1.130000000000000032e-01, 1.181600000000000011e-01,
        1.204199999999999993e-01, 1.280600000000000072e-01, 1.314700000000000035e-01, 1.353800000000000003e-01,
        1.434100000000000097e-01, 1.474000000000000032e-01, 1.529500000000000026e-01, 1.625900000000000123e-01,
        1.703099999999999892e-01, 1.792700000000000127e-01, 1.837499999999999967e-01, 1.886099999999999999e-01,
        1.991999999999999882e-01, 2.076800000000000035e-01, 2.140799999999999925e-01, 2.187300000000000078e-01,
        2.401770000000000016e-01, 2.402310000000000001e-01, 2.400579999999999936e-01, 2.395440000000000069e-01,
        2.395970000000000044e-01, 2.399020000000000041e-01, 2.393129999999999979e-01, 2.390339999999999965e-01,
        2.396459999999999979e-01, 2.432799999999999963e-01, 2.450630000000000031e-01, 2.404970000000000163e-01,
        2.407040000000000013e-01, 2.414990000000000192e-01, 2.446170000000000011e-01, 2.506570000000000187e-01,
        2.568270000000000275e-01, 2.776299999999999879e-01, 2.853109999999999813e-01, 2.855030000000000068e-01,
        2.882720000000000282e-01, 2.923990000000000200e-01, 2.942770000000000108e-01, 2.996820000000000039e-01,
        3.025670000000000304e-01, 3.092230000000000256e-01, 3.167400000000000215e-01, 3.227700000000000014e-01,
        3.266600000000000059e-01, 3.317300000000000249e-01, 3.368900000000000228e-01, 3.391500000000000070e-01,
        3.467900000000000427e-01, 3.502000000000000113e-01, 3.541100000000000358e-01, 3.621400000000000174e-01,
        3.661300000000000110e-01, 3.716800000000000104e-01, 3.813199999999999923e-01, 3.890399999999999969e-01,
        3.980000000000000204e-01, 4.024800000000000044e-01, 4.073400000000000354e-01, 4.179300000000000237e-01,
        4.264100000000000112e-01, 4.328100000000000280e-01, 4.374600000000000155e-01
    ]

    N95_mu_imag_200000 = [
        6.258888748789551215e+01, 1.252130146489693487e+02, 1.253706343760346442e+02, 1.248656662510211248e+02,
        1.233653354794711419e+02, 1.235200402825443575e+02, 1.244103162321726330e+02, 1.226910522226929032e+02,
        1.218766498848220436e+02, 1.236630689587122447e+02, 1.342697357040622705e+02, 1.394732255814030282e+02,
        1.261470524077421942e+02, 1.267512515636827430e+02, 1.290716784920586804e+02, 1.381716623359328366e+02,
        1.557958992450312223e+02, 1.737938961163604858e+02, 2.344265848365437819e+02, 2.567907284523421367e+02,
        2.573495804091721197e+02, 2.654082632845560852e+02, 2.774155647769153461e+02, 2.828780407485270985e+02,
        2.985940403024990815e+02, 3.069793329020024544e+02, 3.263157359629926191e+02, 3.481369114804107880e+02,
        3.656280310361692614e+02, 3.769050365479272386e+02, 3.915946874835032645e+02, 4.065352980500567242e+02,
        4.130758436576705321e+02, 4.351713604405687761e+02, 4.450256625771781387e+02, 4.563188311448487298e+02,
        4.794907818348359569e+02, 4.909937999460491369e+02, 5.069818746610313269e+02, 5.347166795089017342e+02,
        5.568936779849722143e+02, 5.825932376604441743e+02, 5.954265070856914690e+02, 6.093354896192479373e+02,
        6.395956391417718123e+02, 6.637777301111806310e+02, 6.819984815071995854e+02, 6.952204209957068315e+02,
        7.560146998405033401e+02, 7.561673646966717115e+02, 7.556782643523722527e+02, 7.542249726964629417e+02,
        7.543748344710188576e+02, 7.552372075014391157e+02, 7.535717781098542218e+02, 7.527828039395366204e+02,
        7.545133841352422905e+02, 7.647838699967616094e+02, 7.698195269904213092e+02, 7.569193499426881999e+02,
        7.575045063314162235e+02, 7.597515597618071297e+02, 7.685601237414871321e+02, 7.856033087453421331e+02,
        8.029852506758422805e+02, 8.613735615901614437e+02, 8.828439351757772329e+02, 8.833799968641749274e+02,
        8.911075679842978161e+02, 9.026129280209664785e+02, 9.078436509254854627e+02, 9.228809886678320709e+02,
        9.308969546031773916e+02, 9.493625000918116257e+02, 9.701686950016909350e+02, 9.868215200430422556e+02,
        9.975463674222310146e+02, 1.011503000468684832e+03, 1.025682065410677524e+03, 1.031884141755516112e+03,
        1.052813270083236148e+03, 1.062135933263834886e+03, 1.072811135600898979e+03, 1.094685947505485046e+03,
        1.105530439936047060e+03, 1.120587094525696330e+03, 1.146661494338944976e+03, 1.167469897504951859e+03,
        1.191537773538371312e+03, 1.203537808366537320e+03, 1.216529792319103990e+03, 1.244744713613551767e+03,
        1.267242665648303273e+03, 1.284165113394403079e+03, 1.296429080553895346e+03
    ]

    f_N95_mu_imag_200000 = interp1d(N95_b_200000, N95_mu_imag_200000)



    N95_b_300000 = [
        0.000000000000000000e+00, 1.517499999999999969e-03, 1.515099999999999910e-03, 1.516999999999999902e-03,
        1.527900000000000005e-03, 1.538099999999999927e-03, 1.580900000000000100e-03, 1.636499999999999934e-03,
        1.688000000000000047e-03, 3.352099999999999785e-03, 2.677899999999999985e-03, 3.111800000000000069e-03,
        5.971999999999999878e-03, 1.860600000000000101e-02, 2.134799999999999892e-02, 2.415899999999999992e-02,
        2.854999999999999899e-02, 3.081599999999999964e-02, 3.658600000000000046e-02, 4.192799999999999999e-02,
        4.733400000000000107e-02, 5.818600000000000161e-02, 6.004700000000000315e-02, 6.273099999999999510e-02,
        6.670900000000000440e-02, 6.927500000000000324e-02, 7.328199999999999992e-02, 7.641900000000000082e-02,
        8.222899999999999654e-02, 8.432599999999999818e-02, 9.058599999999999985e-02, 1.029800000000000021e-01,
        1.051799999999999957e-01, 1.063700000000000062e-01, 1.121499999999999997e-01, 1.173499999999999960e-01,
        1.210999999999999993e-01, 1.248200000000000004e-01, 1.285300000000000054e-01, 1.319400000000000017e-01,
        1.340600000000000125e-01, 1.440899999999999959e-01, 1.470700000000000063e-01, 1.523700000000000054e-01,
        1.590600000000000069e-01, 1.590399999999999869e-01, 1.590300000000000047e-01, 1.629299999999999915e-01,
        1.681400000000000117e-01, 1.724700000000000122e-01, 1.756800000000000028e-01, 1.786999999999999977e-01,
        1.827699999999999880e-01, 1.869699999999999973e-01, 1.914700000000000013e-01, 1.937399999999999956e-01,
        1.967399999999999982e-01, 1.993499999999999994e-01, 2.040200000000000069e-01, 2.078200000000000047e-01,
        2.102799999999999947e-01, 2.118899999999999950e-01, 2.137900000000000078e-01, 2.168700000000000072e-01,
        2.192900000000000127e-01, 2.208075000000000176e-01, 2.208051000000000041e-01, 2.208070000000000033e-01,
        2.208179000000000114e-01, 2.208280999999999994e-01, 2.208709000000000089e-01, 2.209265000000000256e-01,
        2.209780000000000078e-01, 2.226421000000000094e-01, 2.219679000000000235e-01, 2.224018000000000106e-01,
        2.252620000000000178e-01, 2.378960000000000241e-01, 2.406380000000000186e-01, 2.434490000000000265e-01,
        2.478400000000000047e-01, 2.501059999999999950e-01, 2.558759999999999923e-01, 2.612180000000000057e-01,
        2.666240000000000276e-01, 2.774760000000000004e-01, 2.793370000000000020e-01, 2.820210000000000217e-01,
        2.859990000000000032e-01, 2.885650000000000159e-01, 2.925719999999999987e-01, 2.957089999999999996e-01,
        3.015189999999999815e-01, 3.036159999999999970e-01, 3.098760000000000403e-01, 3.222700000000000009e-01,
        3.244700000000000362e-01, 3.256600000000000050e-01, 3.314400000000000124e-01, 3.366399999999999948e-01,
        3.403900000000000259e-01, 3.441100000000000270e-01, 3.478200000000000180e-01, 3.512300000000000422e-01,
        3.533500000000000529e-01, 3.633800000000000363e-01, 3.663600000000000190e-01, 3.716599999999999904e-01,
        3.783500000000000196e-01, 3.783299999999999996e-01, 3.783199999999999896e-01, 3.822200000000000042e-01,
        3.874300000000000521e-01, 3.917599999999999971e-01, 3.949700000000000433e-01, 3.979900000000000104e-01,
        4.020599999999999730e-01, 4.062600000000000100e-01, 4.107600000000000140e-01, 4.130300000000000082e-01,
        4.160300000000000109e-01, 4.186400000000000121e-01, 4.233100000000000196e-01, 4.271099999999999897e-01,
        4.295700000000000074e-01, 4.311800000000000077e-01, 4.330800000000000205e-01, 4.361599999999999921e-01,
        4.385800000000000254e-01
    ]

    N95_mu_imag_300000 = [
        1.756181723408327571e+02, 1.845988549570703583e+02, 1.845846528605723336e+02, 1.845958961873089947e+02,
        1.846603973272365238e+02, 1.847207561145141312e+02, 1.849740255014061745e+02, 1.853030370275024268e+02,
        1.856077849164832401e+02, 1.954539355485504188e+02, 1.914650761892927449e+02, 1.940322560457522343e+02,
        2.109510406047527908e+02, 2.855962480626757838e+02, 3.017748408644015399e+02, 3.183513507532803146e+02,
        3.442252932381440473e+02, 3.575676682536443423e+02, 3.915088546509189200e+02, 4.228871077318218568e+02,
        4.545932924262377242e+02, 5.180799774611962221e+02, 5.289441271447673216e+02, 5.446001494553167959e+02,
        5.677758802947199683e+02, 5.827068054950420901e+02, 6.059924427689237518e+02, 6.241958549321407190e+02,
        6.578462894455858532e+02, 6.699706530487112559e+02, 7.060952461485622962e+02, 7.772932272702646515e+02,
        7.898837295369773983e+02, 7.966878393171297148e+02, 8.296730084051304175e+02, 8.592558647530803455e+02,
        8.805335194280397673e+02, 9.015931738934341411e+02, 9.225476853439492970e+02, 9.417640486626880829e+02,
        9.536893735427931915e+02, 1.009879183851150401e+03, 1.026498201581098101e+03, 1.055967179019429977e+03,
        1.092999005401408112e+03, 1.092888578908889031e+03, 1.092833365022361932e+03, 1.114334191566044410e+03,
        1.142953585569563529e+03, 1.166646925904136651e+03, 1.184156690635257746e+03, 1.200586557427497155e+03,
        1.222661034581875811e+03, 1.245357646623511073e+03, 1.269580194462734653e+03, 1.281761143556090701e+03,
        1.297819701234995364e+03, 1.311753557741957138e+03, 1.336597686963802971e+03, 1.356729555039318939e+03,
        1.369721561877119029e+03, 1.378206952719550600e+03, 1.388202812710984972e+03, 1.404364985477600840e+03,
        1.417027363670710201e+03, 1.424950996085899760e+03, 1.424938474575723831e+03, 1.424948387440589840e+03,
        1.425005255592900085e+03, 1.425058471063131719e+03, 1.425281761037115984e+03, 1.425571814093363173e+03,
        1.425840462990417109e+03, 1.434513248249285880e+03, 1.431001386296777582e+03, 1.433261833649434948e+03,
        1.448135896378710640e+03, 1.513277196165095575e+03, 1.527291838157360189e+03, 1.541612587572355096e+03,
        1.563887341143171170e+03, 1.575336389342155144e+03, 1.604346352116036314e+03, 1.631018560388125024e+03,
        1.657825242462793994e+03, 1.711062700297024776e+03, 1.720113969454875587e+03, 1.733127022067173812e+03,
        1.752324078369797462e+03, 1.764649710287094422e+03, 1.783806223001519811e+03, 1.798725467925586599e+03,
        1.826174205027885364e+03, 1.836022320877448692e+03, 1.865232852126725675e+03, 1.922219596495109045e+03,
        1.932215497868497778e+03, 1.937607162267353033e+03, 1.963642268429035539e+03, 1.986846013952806061e+03,
        2.003449406480697235e+03, 2.019811257317006948e+03, 2.036020400610236720e+03, 2.050822319999777847e+03,
        2.059977777880296799e+03, 2.102800540528867714e+03, 2.115365109045664667e+03, 2.137529932376849047e+03,
        2.165172673812650373e+03, 2.165090596459965582e+03, 2.165049556515219138e+03, 2.180990835283756496e+03,
        2.202084438434508684e+03, 2.219437668536123510e+03, 2.232197473951539905e+03, 2.244120022148601947e+03,
        2.260061292785456772e+03, 2.276358436925364458e+03, 2.293645602102921202e+03, 2.302297268897693812e+03,
        2.313660080870954971e+03, 2.323479586862361884e+03, 2.340894927303373152e+03, 2.354918804914269003e+03,
        2.363926652175034178e+03, 2.369791796128449278e+03, 2.376682527743611899e+03, 2.387781535621375042e+03,
        2.396440142755071065e+03
    ]

    f_N95_mu_imag_300000 = interp1d(N95_b_300000, N95_mu_imag_300000)


    def f_N95_mu_imag(f, b):
        return AnalyticalCoreData.f_N95_mu_imag_200000(b) + (AnalyticalCoreData.f_N95_mu_imag_300000(b) - AnalyticalCoreData.f_N95_mu_imag_200000(b)) / 100000 * (f - 200000)
