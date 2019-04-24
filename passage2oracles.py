import os

from itertools import combinations
from functools import partial
from ucca import ioutil
from semstr.convert import FROM_FORMAT
from semstr.util.amr import WIKIFIER

from tupa.action import Actions
from tupa.oracle import Oracle
from tupa.config import Config
from tupa.states.state import State

def basename(filename):
    return os.path.basename(os.path.splitext(filename)[0])

def passage_files():
    return [f for dir in ['dev-xml','train-xml'] for f in glob("data/raw/{}/*".format(dir))]

def load_passage(filename, annotate=False):
    WIKIFIER.enabled = False
    converters = {k: partial(c, annotate=annotate) for k, c in FROM_FORMAT.items()}
    passages = ioutil.read_files_and_dirs(filename, converters=converters, attempts=1, delay=0)
    try:
        return next(iter(passages))
    except StopIteration:
        return passages

class Settings:
    SETTINGS = ("implicit", "linkage", "unlabeled")
    VALUES = {"unlabeled": (None, [])}
    INCOMPATIBLE = (("linkage", "unlabeled"),)

    def __init__(self, *args):
        for attr in self.SETTINGS:
            setattr(self, attr, attr in args)

    @classmethod
    def all(cls):
        return [Settings(*c) for n in range(len(cls.SETTINGS) + 1) for c in combinations(cls.SETTINGS, n)
                if not any(all(s in c for s in i) for i in cls.INCOMPATIBLE)]

    def dict(self):
        return {attr: self.VALUES.get(attr, (False, True))[getattr(self, attr)] for attr in self.SETTINGS}

    def list(self):
        return [attr for attr in self.SETTINGS if getattr(self, attr)]

    def suffix(self):
        return "_".join([""] + self.list())

    def __str__(self):
        return "-".join(self.list()) or "default"


def gen_actions(passage):
    oracle = Oracle(passage)
    state = State(passage)
    actions = Actions()
    while True:
        action = min(oracle.get_actions(state, actions).values(), key=str)
        state.transition(action)
        s = str(action)
        if state.need_label:
            label, _ = oracle.get_label(state, action)
            state.label_node(label)
            s += " " + str(label)
        yield s
        if state.finished:
            break

def produce_oracle(filename):
    config = Config()
    setting = Settings(*('implicit', 'linkage')) #TODO: check the format of raw data: 'unlabeled'?
    passage = load_passage(filename)
    config.update(setting.dict())
    config.set_format(passage.extra.get("format") or "ucca")
    store_sequence = "data/oracles/%s%s.txt" % (basename(filename), setting.suffix())
    with open(store_sequence, "w", encoding="utf-8") as f:
        print(passage, file=f)
        for i, action in enumerate(gen_actions(passage)):
            print(action, file=f)



if __name__=="__main__":
    filenames = passage_files()
    for filename in filenames:
        produce_oracle(filename)