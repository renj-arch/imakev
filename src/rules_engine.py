"""Rules engine — learns from feedback, constrains element properties."""
import json, os, re
from pathlib import Path

RULES_PATH = Path(__file__).parent.parent / "rules.json"

DEFAULT_RULES = {
    "element_types": {
        "sun": {
            "scale_min": 2.0, "scale_max": 3.5,
            "y_min": 0.05, "y_max": 0.15,
            "x_min": 0.7, "x_max": 0.95,
            "note": "sun should be small and in upper sky"
        },
        "moon": {
            "scale_min": 2.0, "scale_max": 4.0,
            "y_min": 0.05, "y_max": 0.2,
        },
        "pyramid": {
            "scale_min": 3.0, "scale_max": 10.0,
            "y_min": 0.5, "y_max": 0.85,
        },
        "house": {
            "alias": "building",
            "note": "not a dedicated draw method — redirect to building"
        },
        "leaf": {
            "scale_min": 1.0, "scale_max": 12.0,
        },
        "cat": {
            "scale_min": 2.0, "scale_max": 8.0,
            "y_min": 0.3, "y_max": 0.75,
        },
        "dog": {
            "scale_min": 2.5, "scale_max": 6.0,
            "y_min": 0.5, "y_max": 0.8,
        },
        "rat": {
            "scale_min": 0.8, "scale_max": 5.0,
            "y_min": 0.3, "y_max": 0.85,
        },
        "human": {
            "scale_min": 1.5, "scale_max": 8.0,
            "y_min": 0.4, "y_max": 0.85,
        },
        "temple": {
            "scale_min": 2.0, "scale_max": 7.0,
            "y_min": 0.5, "y_max": 0.85,
        },
        "throne": {
            "scale_min": 3.0, "scale_max": 8.0,
            "y_min": 0.5, "y_max": 0.8,
        },
        "ship": {
            "scale_min": 2.0, "scale_max": 7.0,
            "y_min": 0.55, "y_max": 0.9,
        },
        "building": {
            "scale_min": 1.5, "scale_max": 6.0,
            "y_min": 0.4, "y_max": 0.85,
        },
        "tree": {
            "scale_min": 2.0, "scale_max": 6.0,
            "y_min": 0.55, "y_max": 0.85,
        },
        "fire": {
            "scale_min": 2.0, "scale_max": 8.0,
            "y_min": 0.2, "y_max": 0.65,
        },
        "cloud": {
            "scale_min": 1.5, "scale_max": 5.0,
            "y_min": 0.05, "y_max": 0.35,
        },
    },
    "scene": {
        "element_count_min": 1,
        "element_count_max": 7,
    },
    "forbidden_types": [],
    "feedback_log": [],
}


class RulesEngine:
    """Stores element constraints, applies them to scenes, learns from feedback."""

    def __init__(self, path=None):
        self.path = Path(path) if path else RULES_PATH
        self.rules = self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                merged = dict(DEFAULT_RULES)
                merged.update(data)
                for k, v in DEFAULT_RULES.get("element_types", {}).items():
                    if k not in merged.get("element_types", {}):
                        merged["element_types"][k] = v
                    else:
                        for pk, pv in v.items():
                            merged["element_types"][k].setdefault(pk, pv)
                return merged
            except Exception:
                return dict(DEFAULT_RULES)
        return dict(DEFAULT_RULES)

    def _save(self):
        self.path.write_text(json.dumps(self.rules, indent=2, ensure_ascii=False), encoding="utf-8")

    def constrain_element(self, elem):
        """Clamp element properties to allowed ranges, apply aliases."""
        etype = elem.get("type", "")
        et_rules = self.rules.get("element_types", {}).get(etype, {})

        if et_rules.get("alias"):
            elem["type"] = et_rules["alias"]
            return self.constrain_element(elem)

        if "scale" in elem:
            smin = et_rules.get("scale_min")
            smax = et_rules.get("scale_max")
            if smin is not None:
                elem["scale"] = max(elem["scale"], smin)
            if smax is not None:
                elem["scale"] = min(elem["scale"], smax)

        for axis in ("x", "y"):
            if axis in elem:
                amin = et_rules.get(f"{axis}_min")
                amax = et_rules.get(f"{axis}_max")
                if amin is not None and elem[axis] < amin:
                    elem[axis] = amin
                if amax is not None and elem[axis] > amax:
                    elem[axis] = amax

        return elem

    def validate_scene(self, elements):
        """Apply constraints to every element in a scene."""
        for elem in elements:
            self.constrain_element(elem)
        return elements

    def process_feedback(self, text, element_type=None):
        """Parse natural language feedback and update rules."""
        t = text.lower().strip()
        entry = {"text": text, "element_type": element_type}

        et = element_type
        if et and et not in self.rules["element_types"]:
            self.rules["element_types"][et] = {}

        et_rules = self.rules["element_types"].get(et) if et else None

        action = None

        # "too big" / "high" / "large" / "scale too high"
        if re.search(r'\b(big|large|high|too big|too large|scale.*high|scale.*big)\b', t):
            if et_rules is not None:
                cur = et_rules.get("scale_max")
                if cur is None:
                    cur = 8.0
                et_rules["scale_max"] = round(max(1.5, cur * 0.65), 1)
                action = f"reduced {et} scale_max to {et_rules['scale_max']}"

        # "too small" / "tiny"
        if re.search(r'\b(small|tiny|too small|scale.*low|too low)\b', t):
            if et_rules is not None:
                cur = et_rules.get("scale_min", 1.0)
                et_rules["scale_min"] = round(min(cur * 2.0, 10.0), 1)
                action = f"raised {et} scale_min to {et_rules['scale_min']}"

        # "wrong position" / "wrong place" / "position"
        if re.search(r'\b(wrong|position|place|misplaced|reposition)\b', t):
            if et_rules is not None:
                ax = "y" if re.search(r'\b(y|vertical|height|down|up)\b', t) else "x" if re.search(r'\b(x|horizontal|side)\b', t) else None
                if ax:
                    cur_min = et_rules.get(f"{ax}_min", 0.0)
                    cur_max = et_rules.get(f"{ax}_max", 1.0)
                    if re.search(r'\b(down|lower|below)\b', t):
                        et_rules[f"{ax}_min"] = round(min(cur_min + 0.08, 0.9), 2)
                        et_rules[f"{ax}_max"] = round(min(cur_max + 0.08, 1.0), 2)
                    elif re.search(r'\b(up|higher|above)\b', t):
                        et_rules[f"{ax}_min"] = round(max(cur_min - 0.08, 0.0), 2)
                        et_rules[f"{ax}_max"] = round(max(cur_max - 0.08, 0.1), 2)
                    else:
                        et_rules[f"{ax}_min"] = 0.0
                        et_rules[f"{ax}_max"] = 1.0
                    action = f"adjusted {et} {ax} to [{et_rules.get(f'{ax}_min')}, {et_rules.get(f'{ax}_max')}]"

        # "oval" / "generic" / "fallback" / "not proper" / "random shape"
        if re.search(r'\b(oval|generic|fallback|not proper|random shape|no shape|circle|ellipse)\b', t):
            if et and et not in self.rules["forbidden_types"]:
                self.rules["forbidden_types"].append(et)
                action = f"added {et} to forbidden types"

        # "use X instead of Y" or "X → Y" or "alias"
        # pattern: "use building instead of house"
        m = re.search(r'use\s+(\w+)\s+instead\s+of\s+(\w+)', t)
        if not m:
            m = re.search(r'(\w+)\s*→\s*(\w+)', t)
        if not m:
            m = re.search(r'alias\s+(\w+)\s*[:=]\s*(\w+)', t)
        if m:
            wrong, correct = m.group(2).lower(), m.group(1).lower()
            if wrong not in self.rules["element_types"]:
                self.rules["element_types"][wrong] = {}
            self.rules["element_types"][wrong]["alias"] = correct
            action = f"aliased {wrong} -> {correct}"

        # "too many elements" / "cluttered"
        if re.search(r'\b(too many|cluttered|crowded|busy|overload)\b', t):
            cur = self.rules["scene"]["element_count_max"]
            self.rules["scene"]["element_count_max"] = max(2, cur - 1)
            action = f"reduced element_count_max to {self.rules['scene']['element_count_max']}"

        # "too few" / "sparse" / "empty"
        if re.search(r'\b(too few|sparse|empty|bare|not enough)\b', t):
            cur = self.rules["scene"]["element_count_min"]
            self.rules["scene"]["element_count_min"] = min(cur + 1, self.rules["scene"]["element_count_max"])
            action = f"raised element_count_min to {self.rules['scene']['element_count_min']}"

        entry["action"] = action or "no matching rule"
        self.rules["feedback_log"].append(entry)
        self._save()
        return action


_engine = None


def get_engine(path=None):
    global _engine
    if _engine is None:
        _engine = RulesEngine(path)
    return _engine


def apply_rules(elements, path=None):
    return get_engine(path).validate_scene(elements)


def feedback(text, element_type=None, path=None):
    return get_engine(path).process_feedback(text, element_type)
