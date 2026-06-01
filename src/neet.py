"""NEET concept generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "NEET aspirants, listen up:",
    "This concept is a must-know for NEET:",
    "Most students get this wrong in NEET:",
    "High-yield topic for your NEET exam:",
    "This keeps appearing in NEET papers:",
    "Master this NEET concept once and for all:",
    "Stop missing this question in mock tests:",
    "NEET topper secret: master this concept:",
]

SUBJECTS = [
    "Biology", "Physics", "Chemistry",
    "Zoology", "Botany",
]

FALLBACKS = [
    ("Cell Theory", "All living organisms are composed of cells. The cell is the basic structural and functional unit of life. All cells arise from pre-existing cells. Proposed by Schleiden, Schwann, and Virchow.", "Biology"),
    ("Prokaryotic vs Eukaryotic", "Prokaryotes lack a membrane-bound nucleus. Eukaryotes have a true nucleus and membrane-bound organelles. Bacteria are prokaryotes; plants, animals, fungi are eukaryotes.", "Biology"),
    ("Fluid Mosaic Model", "The plasma membrane is a phospholipid bilayer with embedded proteins. It is fluid and dynamic. Proposed by Singer and Nicolson in 1972.", "Biology"),
    ("Mitochondria", "Double-membrane organelle with inner membrane folded into cristae. Powerhouse of the cell producing ATP via oxidative phosphorylation. Contains its own DNA.", "Biology"),
    ("Endoplasmic Reticulum", "RER has ribosomes and synthesizes proteins. SER lacks ribosomes, synthesizes lipids, detoxifies poisons, stores calcium ions.", "Biology"),
    ("Golgi Apparatus", "Modifies, sorts, and packages proteins. Receives from ER at cis face, releases from trans face. Discovered by Camillo Golgi.", "Biology"),
    ("Lysosomes", "Suicide bags containing hydrolytic enzymes. Digest worn-out organelles and foreign particles. Enzymes work best at acidic pH.", "Biology"),
    ("Nucleus", "Contains genetic material (DNA) surrounded by double membrane nuclear envelope with pores. Nucleolus is site of ribosome synthesis.", "Biology"),
    ("Cell Cycle", "Interphase (G1, S, G2) prepares for division. Mitosis divides nucleus. Cytokinesis divides cytoplasm. G0 is resting phase.", "Biology"),
    ("Mitosis vs Meiosis", "Mitosis: 2 identical diploid cells for growth. Meiosis: 4 non-identical haploid gametes with two divisions. Meiosis creates genetic variation.", "Biology"),
    ("Crossing Over", "Exchange of genetic material between homologous chromosomes in prophase I of meiosis. Increases genetic variation. Occurs at chiasmata.", "Biology"),
    ("Photosynthesis Light Reaction", "Occurs in thylakoids. Light splits water producing O2, ATP, NADPH. Photosystems I and II work in Z-scheme.", "Biology"),
    ("Calvin Cycle", "Dark reaction in stroma. CO2 fixed to glucose using ATP and NADPH. Stages: carboxylation, reduction, regeneration of RuBP.", "Biology"),
    ("C4 Pathway", "Hatch-Slack pathway. CO2 fixed to 4C compound in mesophyll, transferred to bundle sheath. Reduces photorespiration. Example: maize.", "Biology"),
    ("CAM Plants", "Crassulacean acid metabolism. Stomata open at night to fix CO2 into malate. Day: CO2 released for Calvin cycle. Adaptation for arid conditions.", "Biology"),
    ("Photorespiration", "RuBisCO fixes O2 instead of CO2 producing toxic compound. Wasteful process reducing photosynthesis. Common in C3 plants under hot dry conditions.", "Biology"),
    ("Transpiration Pull", "Water rises in xylem due to transpiration from leaves. Cohesion and adhesion create continuous water column. Main force for water ascent.", "Biology"),
    ("Plant Growth Regulators", "Auxins: cell elongation, apical dominance. Gibberellins: stem elongation. Cytokinins: cell division. ABA: stress response. Ethylene: fruit ripening.", "Biology"),
    ("Digestive System", "Alimentary canal: mouth to anus. Accessory organs: liver, pancreas, gallbladder. Mechanical and chemical breakdown of food.", "Biology"),
    ("Breathing Mechanism", "Inspiration: diaphragm contracts, intercostal muscles lift ribs. Expiration: passive relaxation. Intrapleural pressure changes drive air flow.", "Biology"),
    ("Oxygen Transport", "98.5% O2 bound to hemoglobin as oxyhemoglobin. 1.5% dissolved in plasma. Each hemoglobin carries 4 O2. Dissociation curve is sigmoid.", "Biology"),
    ("CO2 Transport", "70% as bicarbonate ions. 20-25% as carbaminohemoglobin. 7% dissolved in plasma. Transported from tissues to lungs.", "Biology"),
    ("Cardiac Cycle", "Atrial systole 0.1s, ventricular systole 0.3s, joint diastole 0.4s. Total 0.8s at 72 bpm. Heart sounds from valve closure.", "Biology"),
    ("ECG Waves", "P wave: atrial depolarization. QRS: ventricular depolarization. T wave: ventricular repolarization. Records electrical activity of heart.", "Biology"),
    ("Nephron", "Functional unit of kidney. Bowman's capsule filters blood. PCT reabsorbs nutrients. Loop of Henle concentrates urine. DCT adjusts electrolyte balance.", "Biology"),
    ("Urine Formation", "Glomerular filtration 125 mL/min. Tubular reabsorption 99%. Tubular secretion. ADH increases water reabsorption. Aldosterone increases Na+ reabsorption.", "Biology"),
    ("Neuron", "Dendrites receive signals. Cell body integrates. Axon transmits. Myelin sheath speeds conduction. Synapse is junction between neurons.", "Biology"),
    ("Synaptic Transmission", "Action potential triggers Ca2+ influx. Neurotransmitters released, bind to receptors on postsynaptic membrane causing excitation or inhibition.", "Biology"),
    ("Endocrine Glands", "Hypothalamus controls pituitary. Thyroid: metabolism. Parathyroid: calcium. Adrenal: stress. Pancreas: blood sugar. Gonads: reproduction.", "Biology"),
    ("Pancreatic Hormones", "Insulin lowers blood glucose. Glucagon raises it. Diabetes mellitus from insulin deficiency or resistance.", "Biology"),
    ("Mendel's Laws", "Segregation: alleles separate in gametes. Independent Assortment: genes on different chromosomes assort independently. Dominance: dominant allele masks recessive.", "Biology"),
    ("DNA Structure", "Double helix. Nucleotides: phosphate, deoxyribose, base (A,T,G,C). A=T (2 bonds), G≡C (3 bonds). Antiparallel strands.", "Biology"),
    ("DNA Replication", "Semiconservative. Helicase unwinds. Polymerase adds nucleotides. Leading: continuous. Lagging: Okazaki fragments. Ligase joins fragments.", "Biology"),
    ("Transcription", "DNA to mRNA by RNA polymerase. Pre-mRNA capped, tailed, spliced in eukaryotes. In nucleus. Initiation, elongation, termination.", "Biology"),
    ("Translation", "mRNA to protein at ribosomes. tRNA carries amino acids. Codon-anticodon pairing. AUG start codon. Initiation, elongation, termination.", "Biology"),
    ("Lac Operon", "Inducible operon. Lactose absent: repressor blocks transcription. Lactose present: binds repressor, allows lac gene transcription.", "Biology"),
    ("Human Genome Project", "Completed 2003. Mapped 3 billion base pairs. 20,000-25,000 protein-coding genes. Only 1.5% DNA codes for proteins.", "Biology"),
    ("Darwin's Natural Selection", "Favorable traits survive and reproduce more leading to evolution. Evidences: fossils, homologous organs, embryology, molecular biology.", "Biology"),
    ("Hardy-Weinberg Principle", "Allele frequencies constant without evolutionary forces. p2 + 2pq + q2 = 1. Affected by mutation, gene flow, drift, selection, non-random mating.", "Biology"),
    ("Human Evolution", "Australopithecus 4 mya, Homo habilis 2.4 mya, Homo erectus 1.8 mya, Neanderthals 0.4 mya, Homo sapiens 0.3 mya. Originated in Africa.", "Biology"),
    ("Immunity Types", "Innate: non-specific, from birth. Acquired: specific, after exposure. Active: body produces antibodies. Passive: ready-made antibodies received.", "Biology"),
    ("HIV and AIDS", "HIV attacks helper T-cells. Transmitted via blood, sex, mother to child. ELISA test detects antibodies. Antiretroviral therapy controls it.", "Biology"),
    ("Cancer Biology", "Uncontrolled cell division from genetic mutations. Proto-oncogenes promote growth. Tumor suppressors inhibit. Treatments: surgery, radiation, chemo, immunotherapy.", "Biology"),
    ("Biotechnology Tools", "Restriction enzymes cut DNA. Vectors: plasmids, viruses. PCR amplifies DNA. Gel electrophoresis separates. Sequencing reads genetic code.", "Biology"),
    ("Recombinant DNA", "Gene inserted into vector. Vector introduced to host. Host expresses desired protein. Used for insulin, growth hormone, vaccines.", "Biology"),
    ("Ecosystem Structure", "Producers make food. Consumers eat others. Decomposers break down dead matter. Trophic levels form food chains. Energy flow is unidirectional.", "Biology"),
    ("Ecological Pyramids", "Numbers: count at each level. Biomass: mass at each level. Energy: energy at each level. Energy pyramid always upright.", "Biology"),
    ("Biogeochemical Cycles", "Carbon: photosynthesis + respiration. Nitrogen: fixation, nitrification, assimilation, ammonification, denitrification. Water: evaporation, condensation, precipitation.", "Biology"),
    ("Biodiversity Hotspots", "Regions with high endemic species under threat. India has 4: Western Ghats, Eastern Himalayas, Indo-Burma, Sundaland.", "Biology"),
    ("In-situ Conservation", "Protecting species in natural habitat. National parks, sanctuaries, biosphere reserves. Example: Jim Corbett National Park.", "Biology"),
    ("Newton's Laws", "First: inertia. Second: F=ma. Third: action-reaction. Inertia resists change in motion.", "Physics"),
    ("Work-Energy Theorem", "Work = change in kinetic energy. W = 0.5mv2 - 0.5mu2. Work = force x displacement in force direction. Unit: Joule.", "Physics"),
    ("Conservation of Energy", "Energy cannot be created or destroyed, only converted. Total mechanical energy (KE+PE) constant without non-conservative forces.", "Physics"),
    ("Gravitation", "F = G(m1m2)/r2. G = 6.67e-11 Nm2/kg2. g = 9.8 m/s2 on Earth. g varies with altitude, depth, latitude.", "Physics"),
    ("Kepler's Laws", "First: elliptical orbits with Sun at focus. Second: equal areas in equal time. Third: T2 proportional to a3.", "Physics"),
    ("Simple Harmonic Motion", "Periodic motion where restoring force proportional to displacement. T = 2pi*sqrt(m/k). Examples: spring, pendulum.", "Physics"),
    ("Wave Motion", "Mechanical waves need medium. Transverse: particles perpendicular to wave. Longitudinal: particles parallel. v = f*lambda.", "Physics"),
    ("Bernoulli's Principle", "In fluid flow, higher velocity = lower pressure. Explains airplane lift, atomizer, venturi meter. P + 0.5pv2 + pgh = constant.", "Physics"),
    ("Thermodynamics First Law", "Energy cannot be created or destroyed. dU = dQ - dW. Internal energy change = heat added - work done.", "Physics"),
    ("Second Law of Thermodynamics", "Entropy of universe always increases. Heat cannot spontaneously flow from cold to hot. Perpetual motion machines impossible.", "Physics"),
    ("Carnot Engine", "Most efficient heat engine. Efficiency = 1 - T2/T1. Reversible cyclic process. Carnot cycle: isothermal + adiabatic expansions and compressions.", "Physics"),
    ("Coulomb's Law", "F = k(q1q2)/r2. Like charges repel, unlike attract. k = 9e9 Nm2/C2. Electric field E = F/q.", "Physics"),
    ("Ohm's Law", "V = IR. Current proportional to voltage at constant temperature. Resistance depends on material, length, cross-section, temperature.", "Physics"),
    ("Kirchhoff's Laws", "Junction rule: sum of currents entering = sum leaving. Loop rule: sum of potential differences in closed loop = 0.", "Physics"),
    ("Magnetic Force", "F = qvBsin(theta). Moving charge in magnetic field experiences force. Lorentz force: F = q(E + vxB).", "Physics"),
    ("Faraday's Law", "Changing magnetic flux induces EMF. EMF = -d(flux)/dt. Lenz's law: induced current opposes change. Basis of generators.", "Physics"),
    ("AC vs DC", "DC: constant direction. AC: periodically reverses. India: 230V, 50Hz. RMS voltage = peak/sqrt(2). AC can be transformed.", "Physics"),
    ("Electromagnetic Waves", "Oscillating electric and magnetic fields perpendicular to each other and direction of propagation. Speed = c = 3e8 m/s. Light is EM wave.", "Physics"),
    ("Ray Optics: Reflection", "Angle of incidence = angle of reflection. Mirror formula: 1/f = 1/u + 1/v. Concave: real/inverted. Convex: virtual/upright.", "Physics"),
    ("Refraction", "Snell's law: n1sin(i) = n2sin(r). Light bends toward normal in denser medium. Refractive index n = c/v. Total internal reflection above critical angle.", "Physics"),
    ("Lens Formula", "1/f = 1/v - 1/u. Power P = 1/f (diopters). Convex: converging, positive power. Concave: diverging, negative power. Lens maker's formula.", "Physics"),
    ("Photoelectric Effect", "Light ejects electrons from metal surface. Einstein: light as photons, E = hf. Kinetic energy of ejected electron = hf - work function.", "Physics"),
    ("Bohr's Model", "Electrons in quantized orbits. Angular momentum = nh/2pi. Energy levels: En = -13.6/n2 eV. Transitions produce spectral lines.", "Physics"),
    ("Nuclear Fission", "Heavy nucleus splits into lighter ones releasing energy. Chain reaction. Used in nuclear reactors and atomic bombs. Critical mass needed.", "Physics"),
    ("Semi-conductors", "Conductivity between conductor and insulator. Doping: adding impurities. n-type: extra electrons. p-type: holes. PN junction: diode.", "Physics"),
    ("Structure of Atom", "Rutherford: nucleus at center with electrons orbiting. Bohr: quantized energy levels. Thomson: plum pudding model. Chadwick: discovered neutron.", "Chemistry"),
    ("Chemical Bonding", "Ionic: electron transfer, electrostatic attraction. Covalent: electron sharing. Metallic: delocalized electrons. VSEPR theory predicts shape.", "Chemistry"),
    ("VSEPR Theory", "Valence Shell Electron Pair Repulsion. Electron pairs arrange to minimize repulsion. Determines molecular geometry. Examples: linear, bent, tetrahedral.", "Chemistry"),
    ("Hybridization", "Mixing of atomic orbitals to form equivalent hybrid orbitals. sp (linear), sp2 (trigonal planar), sp3 (tetrahedral). Explains bond angles.", "Chemistry"),
    ("Thermodynamics in Chemistry", "Enthalpy H = U + PV. Exothermic: dH negative. Endothermic: dH positive. Gibbs free energy dG = dH - TdS. Spontaneous when dG negative.", "Chemistry"),
    ("Chemical Equilibrium", "Forward rate = reverse rate. Kc = products/reactants. Le Chatelier's principle: system shifts to oppose change. Effect of temperature, pressure, concentration.", "Chemistry"),
    ("Electrochemistry", "Electrochemical cells convert chemical to electrical energy. Anode: oxidation. Cathode: reduction. EMF = Ered(cathode) - Ered(anode). Nernst equation.", "Chemistry"),
    ("Redox Reactions", "Oxidation: loss of electrons. Reduction: gain of electrons. Oxidizing agent accepts electrons. Reducing agent donates electrons. Balancing half-reactions.", "Chemistry"),
    ("Chemical Kinetics", "Rate of reaction = d[conc]/dt. Order: sum of exponents in rate law. Activation energy: minimum energy for reaction. Catalyst lowers activation energy.", "Chemistry"),
    ("Organic Chemistry Basics", "Carbon compounds. Tetravalent. Single bonds: alkane. Double: alkene. Triple:alkyne. Functional groups determine properties. IUPAC naming.", "Chemistry"),
    ("Hydrocarbons", "Alkanes: CnH2n+2, saturated. Alkenes: CnH2n, unsaturated. Alkynes: CnH2n-2. Aromatic: benzene ring. Combustion, substitution, addition reactions.", "Chemistry"),
    ("Alcohols, Phenols, Ethers", "Alcohols: -OH group. Phenols: -OH on benzene. Ethers: R-O-R. Preparation from alkenes, haloalkanes. Oxidation: alcohol to aldehyde to carboxylic acid.", "Chemistry"),
    ("Aldehydes and Ketones", "Carbonyl group C=O. Aldehydes: terminal carbonyl. Ketones: internal. Nucleophilic addition reactions. Fehling's test distinguishes aldehydes.", "Chemistry"),
    ("Carboxylic Acids", "-COOH group. Weak acids. Reactions: esterification, reduction, decarboxylation. Acetic acid most common. Formic acid in ant venom.", "Chemistry"),
    ("Amines", "Derivatives of ammonia. Primary: one alkyl group. Secondary: two. Tertiary: three. Quaternary ammonium salts. Basic nature. Diazotization reaction.", "Chemistry"),
    ("Biomolecules: Carbohydrates", "Monosaccharides: glucose, fructose. Disaccharides: sucrose, maltose. Polysaccharides: starch, cellulose. Reducing sugars have free aldehyde group.", "Chemistry"),
    ("Biomolecules: Proteins", "Polymers of amino acids. Peptide bonds link amino acids. Primary: sequence. Secondary: alpha helix, beta sheet. Tertiary: 3D folding. Quaternary: multiple subunits.", "Chemistry"),
    ("Polymers", "Addition polymers: polyethylene, PVC, polystyrene. Condensation polymers: nylon, polyester, proteins. Natural: rubber, cellulose. Synthetic: plastics, fibers.", "Chemistry"),
    ("s-Block Elements", "Group 1 (alkali metals) and Group 2 (alkaline earth metals). Highly reactive. ns1 and ns2 configuration. Hydration enthalpy decreases down group.", "Chemistry"),
    ("p-Block Elements", "Groups 13-18. Boron family to noble gases. Variable oxidation states. Trends in metallic character, ionization energy, electronegativity down groups.", "Chemistry"),
    ("d and f Block Elements", "Transition metals (d-block): variable oxidation states, colored compounds, catalytic properties. Lanthanoids and actinoids (f-block): inner transition elements.", "Chemistry"),
    ("Coordination Compounds", "Central metal ion bonded to ligands. Coordination number. Chelate effect. Crystal field theory explains color and magnetism. Important in bioinorganic chemistry.", "Chemistry"),
    ("Solutions and Colligative Properties", "Raoult's law: vapor pressure lowering. Boiling point elevation. Freezing point depression. Osmotic pressure. dTb = Kb*m. i = van't Hoff factor.", "Chemistry"),
    ("States of Matter", "Gas: no fixed shape/volume. Liquid: fixed volume, no shape. Solid: fixed shape and volume. Ideal gas law: PV = nRT. Real gases deviate at high pressure.", "Chemistry"),
]

def generate_neet_script() -> dict:
    entry = bank_manager.pick("neet")
    if entry:
        print(f"  Using banked neet ({bank_manager.count('neet')} left)")
        return entry

    print("  Bank empty, generating fresh NEET concepts...")
    return _try_llm() or _fallback()

def _fallback() -> dict:
    concepts = random.sample(FALLBACKS, min(4, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"cinematic educational illustration: {topic}, NEET exam preparation, biology chemistry physics, clean professional style, 9:16 vertical, dark green and gold theme, highly detailed"
        for topic, _, _ in concepts
    ]
    tts_lines = [f"{topic}. {explanation}" for topic, explanation, _ in concepts]
    return {
        "title": f"NEET: {concepts[0][0]}",
        "hook": hook,
        "topics": [t for t, _, _ in concepts],
        "explanations": [e for _, e, _ in concepts],
        "subjects": [s for _, _, s in concepts],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }

def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 4 different NEET exam concepts to explain in a short video. "
            "Each should be a high-yield topic from Biology, Physics, or Chemistry based on NCERT Class 11 and 12 syllabus. "
            "Format exactly:\n"
            "TOPIC: [Name of the concept]\n"
            "EXPLANATION: [2-3 sentence clear explanation as if teaching a beginner]\n"
            "SUBJECT: [Biology/Physics/Chemistry]\n\n"
            "Make explanations simple, accurate, and exam-focused. Focus on topics that appear in NEET UG."
        )
        system = "You are a NEET mentor teaching complex topics in simple words. Only include verified facts from NCERT."
        raw = _generate(prompt, temperature=0.8, max_tokens=800, system=system)
        if not raw:
            return None
        concepts = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                if current.get("topic") and current.get("explanation"):
                    concepts.append((current["topic"], current["explanation"], current.get("subject", "Biology")))
                current = {"topic": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("SUBJECT:") and current:
                current["subject"] = line.split(":", 1)[-1].strip()
        if current.get("topic") and current.get("explanation"):
            concepts.append((current["topic"], current["explanation"], current.get("subject", "Biology")))
        if concepts and len(concepts) >= 2:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"cinematic educational illustration: {t}, NEET exam preparation, biology chemistry physics, clean professional style, 9:16 vertical, dark green and gold theme, highly detailed"
                for t, _, _ in concepts
            ]
            tts_lines = [f"{t}. {e}" for t, e, _ in concepts]
            return {
                "title": f"NEET: {concepts[0][0]}",
                "hook": hook,
                "topics": [t for t, _, _ in concepts],
                "explanations": [e for _, e, _ in concepts],
                "subjects": [s for _, _, s in concepts],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
