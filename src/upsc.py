"""UPSC concept generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "UPSC aspirants, listen up:",
    "This concept is a must-know for prelims:",
    "Most students confuse this UPSC topic:",
    "Here's a high-weightage concept for your exam:",
    "One concept that keeps appearing in UPSC papers:",
    "Clear this UPSC topic once and for all:",
    "Stop getting this question wrong in mock tests:",
    "UPSC topper secret: master this concept:",
]

SUBJECTS = [
    "Polity", "Economy", "History", "Geography",
    "Environment", "Science & Tech", "Art & Culture",
    "International Relations", "Society", "Governance",
]

FALLBACKS = [
    ("Fiscal Deficit", "The difference between the government's total expenditure and its total revenue excluding borrowing. A high deficit means the government is spending beyond its means and borrowing to cover the gap. It's a key indicator of economic health.", "Economy"),
    ("Fundamental Rights", "Six fundamental rights guaranteed by the Indian Constitution — Right to Equality, Freedom, Against Exploitation, Freedom of Religion, Cultural/Educational Rights, and Right to Constitutional Remedies. Article 32 is the 'heart and soul' of the Constitution.", "Polity"),
    ("Monsoon Mechanism", "The southwest monsoon is driven by the differential heating of land and sea. The Tibetan Plateau acts as a heat source, creating a low-pressure zone that draws moist air from the Indian Ocean. It arrives in Kerala by June 1st.", "Geography"),
    ("Battle of Plassey", "Fought in 1757 between the British East India Company and Siraj-ud-Daulah. Robert Clive bribed Mir Jafar, the Nawab's commander, who betrayed him. This battle marked the beginning of British political control in India.", "History"),
    ("Directive Principles", "Article 36-51 of the Indian Constitution. They are non-justiciable guidelines for the state to create a welfare state. Inspired by the Irish Constitution. They aim to secure social and economic justice for all citizens.", "Polity"),
    ("Greenhouse Effect", "The trapping of heat by greenhouse gases like CO2, methane, and water vapor in Earth's atmosphere. Without it, Earth would be -18°C. Human activities have intensified it, causing global warming and climate change.", "Environment"),
    ("WTO and India", "The World Trade Organization replaced GATT in 1995. India is a founding member. Key issues for India include agricultural subsidies, intellectual property rights under TRIPS, and special and differential treatment for developing nations.", "International Relations"),
    ("Right to Information", "Enacted in 2005, RTI empowers citizens to seek information from public authorities. It promotes transparency and accountability in government functioning. Any citizen can file an RTI application for a nominal fee.", "Polity"),
    ("Inflation Types", "Demand-pull inflation occurs when demand exceeds supply. Cost-push inflation happens when production costs rise. Built-in inflation is caused by adaptive expectations. The RBI uses repo rate to control inflation.", "Economy"),
    ("Western Ghats", "A UNESCO World Heritage Site and one of the world's eight hottest biodiversity hotspots. They run parallel to India's west coast, spanning 1600 km. Receive heavy rainfall and host over 7,000 species of flowering plants.", "Geography"),
    ("Preamble of India", "The Preamble declares India as a Sovereign, Socialist, Secular, Democratic Republic. It was adopted on 26 November 1949. The words 'Socialist' and 'Secular' were added by the 42nd Amendment in 1976.", "Polity"),
    ("Banking Structure in India", "RBI is the supreme monetary authority. Scheduled commercial banks include public sector (SBI, PNB), private sector (HDFC, ICICI), foreign banks, and regional rural banks. NBFCs lend but don't accept demand deposits.", "Economy"),
    ("Harappan Civilization", "One of the three great ancient civilizations, along with Egypt and Mesopotamia. Known for advanced urban planning with grid-pattern streets, drainage systems, and standardized bricks. Major sites: Harappa, Mohenjo-Daro, Dholavira.", "History"),
    ("NAPCC", "India's National Action Plan on Climate Change has 8 national missions including Solar Mission, Water Mission, and Green India Mission. Launched in 2008. Aims to promote sustainable development while addressing climate change.", "Environment"),
    ("Lok Sabha vs Rajya Sabha", "Lok Sabha is the lower house with 543 elected members, term of 5 years. Rajya Sabha is the upper house with 245 members, 12 nominated by President, 233 elected by states. Rajya Sabha is permanent but 1/3 retires every 2 years.", "Polity"),
]

UPSC_SUBJECTS = [
    "Polity", "Economy", "History", "Geography",
    "Environment", "Science & Tech", "Art & Culture",
    "International Relations", "Society", "Governance",
]


def generate_upsc_script() -> dict:
    entry = bank_manager.pick("upsc")
    if entry:
        print(f"  Using banked upsc ({bank_manager.count('upsc')} left)")
        return entry

    print("  Bank empty, generating fresh UPSC concepts...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    concepts = random.sample(FALLBACKS, min(4, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"cinematic educational illustration: {topic}, Indian government building background, clean professional style, 9:16 vertical, dark blue and gold theme, highly detailed, upsc exam preparation theme"
        for topic, _, _ in concepts
    ]
    tts_lines = [f"{topic}. {explanation}" for topic, explanation, _ in concepts]
    return {
        "title": f"UPSC: {concepts[0][0]}",
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
            "Give me 4 different UPSC exam concepts to explain in a short video. "
            "Each should be a high-yield topic from Polity, Economy, History, or Geography. "
            "Format exactly:\n"
            "TOPIC: [Name of the concept]\n"
            "EXPLANATION: [2-3 sentence clear explanation as if teaching a beginner]\n"
            "SUBJECT: [Polity/Economy/History/Geography]\n\n"
            "Make explanations simple, accurate, and exam-focused."
        )
        system = "You are a UPSC mentor teaching complex topics in simple words. Only include verified facts."
        raw = _generate(prompt, temperature=0.8, max_tokens=800, system=system)
        if not raw:
            return None
        concepts = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                if current.get("topic") and current.get("explanation"):
                    concepts.append((current["topic"], current["explanation"], current.get("subject", "Polity")))
                current = {"topic": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("SUBJECT:") and current:
                current["subject"] = line.split(":", 1)[-1].strip()
        if current.get("topic") and current.get("explanation"):
            concepts.append((current["topic"], current["explanation"], current.get("subject", "Polity")))
        if concepts and len(concepts) >= 2:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"cinematic educational illustration: {t}, Indian government building background, clean professional style, 9:16 vertical, dark blue and gold theme, highly detailed, upsc exam preparation theme"
                for t, _, _ in concepts
            ]
            tts_lines = [f"{t}. {e}" for t, e, _ in concepts]
            return {
                "title": f"UPSC: {concepts[0][0]}",
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
