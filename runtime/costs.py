"""Local user-configurable model-request safeguards. USD budgets are advisory until verified metering."""
import threading
try:
    from . import products
except ImportError:
    import products

LOCK = threading.RLock()
DEFAULT = {'maxOutputTokens': 1800, 'maxModelCalls': 6, 'monthlyBudgetUsd': 60, 'perTaskBudgetUsd': 12}


def current():
    raw = products.read_json(products.STATE/'cost-controls.json', {})
    return {**DEFAULT, **{k: raw[k] for k in DEFAULT if k in raw}}


def update(data):
    if not isinstance(data,dict) or set(data) != set(DEFAULT):
        raise products.ProductError('All four cost control fields are required')
    limits={'maxOutputTokens':(256,8192),'maxModelCalls':(2,8),
            'monthlyBudgetUsd':(1,10000),'perTaskBudgetUsd':(1,5000)}
    for k,(lo,hi) in limits.items():
        v=data[k]
        if type(v) is not int or not lo<=v<=hi:
            raise products.ProductError(f'{k} must be an integer between {lo} and {hi}')
    if data['perTaskBudgetUsd'] > data['monthlyBudgetUsd']:
        raise products.ProductError('Per-task advisory budget cannot exceed monthly budget')
    with LOCK:
        products.write_json(products.STATE/'cost-controls.json',data)
        return current()
