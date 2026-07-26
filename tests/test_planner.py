import pandas as pd

from runbeat.planner import WORKOUTS, infer_cadence, personalize_plan, target_curve


def test_infer_cadence():
    frame = pd.DataFrame({"cadence": [158, 160, 162]})
    assert infer_cadence(frame) == 160


def test_personalize_plan_is_bounded():
    plan = personalize_plan(WORKOUTS["Easy"], 180)
    assert plan.start_bpm == WORKOUTS["Easy"].start_bpm + 4


def test_target_curve_reaches_finish():
    plan = WORKOUTS["Progression"]
    curve = target_curve(plan, 9)
    assert curve[0] == plan.start_bpm
    assert curve[-1] == plan.finish_bpm
