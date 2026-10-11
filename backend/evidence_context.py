"""Bound model context while retaining complete quantitative evidence in storage."""
def bounded(value,depth=0):
    if isinstance(value,dict):
        return {key:bounded(item,depth+1) for key,item in value.items() if key not in ('path','history','cases')}
    if isinstance(value,list):
        if len(value)>8:
            return {'items': [bounded(item,depth+1) for item in value[:8]],'total_items':len(value),'truncated_for_model_context':True}
        return [bounded(item,depth+1) for item in value]
    if isinstance(value,str) and len(value)>2000:
        return value[:2000]+' [truncated for model context]'
    return value
