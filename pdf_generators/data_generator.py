"""
data_generator.py — Shared manufacturing data factory.

Generates a consistent universe of 200 machines, 10 production lines,
20 suppliers, 50 chemicals, and 30 technicians.
All PDF generators import FACTORY from here to keep data consistent.
"""

import random
import datetime
from dataclasses import dataclass, field
from typing import List, Dict
from faker import Faker


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Machine:
    machine_id: str        # M001–M200
    model: str
    manufacturer: str
    machine_type: str
    production_line: str   # L1–L10
    bay: str
    install_date: str
    supplier_id: str
    rpm_max: int
    power_kw: float
    weight_kg: int
    tolerance_mm: float
    axes: int


@dataclass
class Supplier:
    supplier_id: str       # S001–S020
    name: str
    contact: str
    email: str
    phone: str
    lead_time_days: int
    part_categories: List[str]
    rating: float
    country: str


@dataclass
class Chemical:
    sku: str
    name: str
    chem_type: str
    cas_number: str
    flash_point_c: float
    storage_temp_max_c: float
    supplier_id: str
    hazard_class: str
    ghs_pictograms: List[str]
    viscosity_cst: float


@dataclass
class Technician:
    tech_id: str           # T001–T030
    name: str
    certification: str
    shift: str
    specialization: str
    years_exp: int


@dataclass
class ProductionLine:
    line_id: str           # L1–L10
    name: str
    product_type: str
    target_units_per_hour: int
    defect_threshold_pct: float
    supervisor: str
    machine_count: int


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class ManufacturingDataFactory:
    """
    Fixed-seed manufacturing universe. Import the FACTORY singleton.
    Call get_rng(doc_seed) for per-document reproducible randomness.
    """

    MACHINE_TYPES = [
        "CNC Machining Center", "Hydraulic Press", "Industrial Robot",
        "Conveyor System", "CNC Lathe", "Milling Machine",
        "Injection Molder", "Welding Robot", "Assembly Station",
        "Quality Scanner", "CMM (Coordinate Measuring)",
        "Surface Grinder", "EDM Machine", "Laser Cutter", "Punch Press",
    ]

    MANUFACTURERS = [
        "Haas Automation", "Fanuc America", "Mazak Corporation",
        "DMG Mori", "Okuma America", "ABB Robotics",
        "KUKA Systems", "Siemens Industry", "Bosch Rexroth",
        "Mitsubishi Electric",
    ]

    PART_CATEGORIES = [
        "Spindles", "Bearings", "Coolant Systems", "Control Boards",
        "Servo Motors", "Hydraulic Seals", "Cutting Tools",
        "Fasteners", "Sensors", "Lubricants", "Linear Guides",
        "Ball Screws", "Tooling", "Pneumatic Actuators",
    ]

    GHS_PICTOGRAMS = [
        "GHS01-Explosive", "GHS02-Flammable", "GHS03-Oxidizer",
        "GHS04-Compressed Gas", "GHS05-Corrosive", "GHS06-Acute Toxic",
        "GHS07-Irritant", "GHS08-Health Hazard", "GHS09-Environmental",
    ]

    CHEM_NAMES = {
        "lubricant": [
            "ISO VG 32 Spindle Oil", "ISO VG 46 Hydraulic Oil",
            "ISO VG 68 Way Oil", "ISO VG 100 Gear Oil",
            "ISO VG 150 Slideway Oil", "EP-2 Lithium Grease",
            "NLGI-2 Calcium Grease", "Moly Disulfide Paste",
            "Chain & Cable Lubricant", "Penetrating Oil PX-40",
        ],
        "coolant": [
            "Water-Soluble Coolant 5%", "Semi-Synthetic Coolant 8%",
            "Full Synthetic Coolant 10%", "Straight Cutting Oil",
            "Aluminium Cutting Fluid", "Grinding Coolant Concentrate",
            "High-Pressure Coolant HPC-7", "Bio-Stable Coolant BS-3",
        ],
        "solvent": [
            "Isopropanol 99% Technical", "Acetone Industrial Grade",
            "Mineral Spirits VM&P", "Parts Wash Solvent PW-1",
            "Brake Cleaner Aerosol", "Degreaser HD-7",
        ],
        "adhesive": [
            "Loctite 243 Blue Threadlocker", "Loctite 271 Red Threadlocker",
            "Epoxy Adhesive 2-Part", "Cyanoacrylate Fast-Set",
            "Thread Sealant PTFE", "Anti-Seize Compound",
        ],
    }

    CERTIFICATIONS = [
        "ISO 9001 Internal Auditor", "AWS Certified Welding Inspector",
        "PLC Programming Level 3", "Hydraulics Specialist IFPS",
        "Six Sigma Green Belt", "Lean Manufacturing Practitioner",
        "OSHA 30-Hour Safety", "CNC Programming Advanced",
        "Robotics Technician ABB", "Metrology Technician CMM",
    ]

    PRODUCT_TYPES = [
        "Precision Gear Assemblies", "Structural Aluminium Brackets",
        "Engine Cylinder Heads", "Hydraulic Manifold Blocks",
        "Aerospace Titanium Fittings", "Automotive Body Stampings",
        "Medical Device Housings", "Electronic Enclosures",
        "Power Transmission Shafts", "Fluid Control Valve Bodies",
    ]

    SUPPLIER_NAMES = [
        "Haas Automation Inc.", "Fanuc America Corp.", "Mazak Corporation",
        "DMG Mori USA", "Okuma America Corp.", "ABB Robotics Inc.",
        "KUKA Systems NA", "Siemens Industry Inc.", "Bosch Rexroth Corp.",
        "SKF Bearing Solutions", "NSK Precision Parts", "Parker Hannifin Corp.",
        "Eaton Hydraulics", "Henkel Industrial Adhesives", "Castrol Industrial",
        "Shell Lubricants NA", "Sandvik Coromant", "Kennametal Inc.",
        "Mitutoyo America Corp.", "Renishaw Inc.",
    ]

    def __init__(self):
        self._fake = Faker()
        self._fake.seed_instance(42)
        self._rng = random.Random(42)

        self.machines: Dict[str, Machine] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.chemicals: Dict[str, Chemical] = {}
        self.technicians: Dict[str, Technician] = {}
        self.production_lines: Dict[str, ProductionLine] = {}

        self._build_universe()

    # ------------------------------------------------------------------
    def _build_universe(self):
        self._build_suppliers()
        self._build_production_lines()
        self._build_machines()
        self._build_chemicals()
        self._build_technicians()

    def _build_suppliers(self):
        countries = ["USA", "Germany", "Japan", "Sweden", "UK", "Switzerland"]
        for i, name in enumerate(self.SUPPLIER_NAMES, 1):
            sid = f"S{i:03d}"
            cats = self._rng.sample(self.PART_CATEGORIES, k=self._rng.randint(2, 5))
            self.suppliers[sid] = Supplier(
                supplier_id=sid,
                name=name,
                contact=self._fake.name(),
                email=self._fake.company_email(),
                phone=self._fake.phone_number(),
                lead_time_days=self._rng.randint(3, 45),
                part_categories=cats,
                rating=round(self._rng.uniform(2.8, 5.0), 1),
                country=self._rng.choice(countries),
            )

    def _build_production_lines(self):
        sup_fake = Faker()
        sup_fake.seed_instance(7777)
        for i in range(1, 11):
            lid = f"L{i}"
            self.production_lines[lid] = ProductionLine(
                line_id=lid,
                name=f"Production Line {i}",
                product_type=self.PRODUCT_TYPES[i - 1],
                target_units_per_hour=self._rng.randint(40, 220),
                defect_threshold_pct=round(self._rng.uniform(1.2, 3.5), 1),
                supervisor=sup_fake.name(),
                machine_count=self._rng.randint(8, 25),
            )

    def _build_machines(self):
        line_ids = list(self.production_lines.keys())
        supplier_ids = list(self.suppliers.keys())
        base_date = datetime.date(2014, 1, 1)
        mfr_cycle = (self.MANUFACTURERS * 20)[:200]
        type_cycle = (self.MACHINE_TYPES * 14)[:200]

        for i in range(1, 201):
            mid = f"M{i:03d}"
            mtype = type_cycle[i - 1]
            mfr = mfr_cycle[i - 1]
            offset = self._rng.randint(0, 365 * 9)
            install_date = base_date + datetime.timedelta(days=offset)
            axes = self._rng.choice([3, 4, 5]) if "CNC" in mtype else self._rng.choice([1, 2, 3])
            self.machines[mid] = Machine(
                machine_id=mid,
                model=f"{mfr.split()[0]}-{self._rng.randint(100, 9999)}",
                manufacturer=mfr,
                machine_type=mtype,
                production_line=self._rng.choice(line_ids),
                bay=f"Bay-{self._rng.randint(1, 20):02d}",
                install_date=install_date.isoformat(),
                supplier_id=self._rng.choice(supplier_ids),
                rpm_max=self._rng.randint(800, 18000),
                power_kw=round(self._rng.uniform(4.0, 90.0), 1),
                weight_kg=self._rng.randint(400, 15000),
                tolerance_mm=self._rng.choice([0.001, 0.005, 0.01, 0.025, 0.05]),
                axes=axes,
            )

    def _build_chemicals(self):
        supplier_ids = list(self.suppliers.keys())
        all_chems = []
        for ctype, names in self.CHEM_NAMES.items():
            for name in names:
                all_chems.append((ctype, name))
        # pad to 50
        extra_types = list(self.CHEM_NAMES.keys())
        while len(all_chems) < 50:
            ct = self._rng.choice(extra_types)
            all_chems.append((ct, f"{ct.title()} Grade {len(all_chems) + 1}"))

        cas_base = 64000
        for i, (ctype, name) in enumerate(all_chems[:50], 1):
            sku = f"CHM-{i:04d}"
            flash = float(self._rng.randint(50, 250)) if ctype != "coolant" else 0.0
            self.chemicals[sku] = Chemical(
                sku=sku,
                name=name,
                chem_type=ctype,
                cas_number=f"{cas_base + i}-{self._rng.randint(10, 99)}-{self._rng.randint(1, 9)}",
                flash_point_c=flash,
                storage_temp_max_c=float(self._rng.randint(35, 80)),
                supplier_id=self._rng.choice(supplier_ids),
                hazard_class=self._rng.choice([
                    "3 - Flammable Liquid", "8 - Corrosive",
                    "9 - Miscellaneous", "6.1 - Toxic", "None - Non-Hazardous",
                ]),
                ghs_pictograms=self._rng.sample(
                    self.GHS_PICTOGRAMS, k=self._rng.randint(1, 3)
                ),
                viscosity_cst=round(self._rng.uniform(10.0, 460.0), 1),
            )

    def _build_technicians(self):
        tech_fake = Faker()
        tech_fake.seed_instance(1234)
        for i in range(1, 31):
            tid = f"T{i:03d}"
            self.technicians[tid] = Technician(
                tech_id=tid,
                name=tech_fake.name(),
                certification=self._rng.choice(self.CERTIFICATIONS),
                shift=self._rng.choice(["Day", "Night", "Swing"]),
                specialization=self._rng.choice(self.MACHINE_TYPES[:8]),
                years_exp=self._rng.randint(2, 25),
            )

    # ------------------------------------------------------------------
    # Per-document helpers
    # ------------------------------------------------------------------

    def get_rng(self, doc_seed: int) -> random.Random:
        """Return a seeded RNG for reproducible per-document data."""
        return random.Random(doc_seed)

    def machines_for_line(self, line_id: str) -> List[Machine]:
        return [m for m in self.machines.values() if m.production_line == line_id]

    def random_machines(self, n: int, seed: int) -> List[Machine]:
        rng = self.get_rng(seed)
        return rng.sample(list(self.machines.values()), k=min(n, 200))

    def random_suppliers(self, n: int, seed: int) -> List[Supplier]:
        rng = self.get_rng(seed)
        return rng.sample(list(self.suppliers.values()), k=min(n, 20))

    def random_chemicals(self, n: int, seed: int) -> List[Chemical]:
        rng = self.get_rng(seed)
        return rng.sample(list(self.chemicals.values()), k=min(n, 50))

    def random_technicians(self, n: int, seed: int) -> List[Technician]:
        rng = self.get_rng(seed)
        return rng.sample(list(self.technicians.values()), k=min(n, 30))

    def quarter_date_range(self, seed: int, year: int = 2025):
        """Return (start_date, end_date) for a random quarter."""
        rng = self.get_rng(seed)
        q = rng.randint(1, 4)
        starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
        ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
        return (
            datetime.date(year, *starts[q]),
            datetime.date(year, *ends[q]),
        )

    def week_date_range(self, seed: int, year: int = 2025):
        """Return (start_date, end_date) for a random week."""
        rng = self.get_rng(seed)
        week_num = rng.randint(1, 52)
        start = datetime.date.fromisocalendar(year, week_num, 1)
        end = start + datetime.timedelta(days=6)
        return start, end

    def part_number(self, seed: int, prefix: str = "PN") -> str:
        rng = self.get_rng(seed)
        return f"{prefix}-{rng.randint(10000, 99999)}-{rng.choice('ABCDEFGHJK')}"

    def work_order(self, seed: int) -> str:
        rng = self.get_rng(seed)
        return f"WO-{rng.randint(100000, 999999)}"

    def serial_number(self, seed: int) -> str:
        rng = self.get_rng(seed)
        return f"SN-{rng.randint(1000000, 9999999)}"


# ---------------------------------------------------------------------------
# Singleton — all PDF generators import this
# ---------------------------------------------------------------------------
FACTORY = ManufacturingDataFactory()
