"""Offline, deterministic model-provider adapter for the Strands agent loop.

This is explicitly a rule router, not a language model. It exercises the same
agent/tool protocol as Ollama and Bedrock without requiring paid credentials.
"""
from strands.models.model import Model

def route_text(text):
    text = text.lower()
    return 'scenario' if any(word in text for word in ('what if','double','shift','scenario','rain','cloud','burning','wind speed','humidity')) else 'impact' if any(word in text for word in ('exposure','population','hospital','how many','district')) else 'strategy' if any(word in text for word in ('advis','principal','parent','should','school guidance')) else 'intelligence' if any(word in text for word in ('data','news','latest','source','fires','station')) else 'forecast'

class EvidenceRouterModel(Model):
    def update_config(self,**config):
        self.config = config

    def get_config(self):
        return getattr(self,'config',{})

    async def structured_output(self,*args,**kwargs):
        raise NotImplementedError('Local rule router supports tool evidence, not generated structured output')
        yield

    async def stream(self,messages,tool_specs=None,system_prompt=None,**kwargs):
        last = messages[-1]['content']
        is_result = any('toolResult' in block for block in last)
        yield {'messageStart':{'role':'assistant'}}
        if is_result or not tool_specs:
            yield {'contentBlockStart':{'contentBlockIndex':0,'start':{}}}
            yield {'contentBlockDelta':{'contentBlockIndex':0,'delta':{'text':'Tool evidence collected.'}}}
            yield {'contentBlockStop':{'contentBlockIndex':0}}
            yield {'messageStop':{'stopReason':'end_turn'}}
        else:
            query = ' '.join(block.get('text','') for block in last)
            chosen = route_text(query)+'_agent'
            tool_name = next((spec['name'] for spec in tool_specs if spec['name']==chosen),tool_specs[0]['name'])
            yield {'contentBlockStart':{'contentBlockIndex':0,'start':{'toolUse':{'toolUseId':'evidence-call','name':tool_name}}}}
            yield {'contentBlockDelta':{'contentBlockIndex':0,'delta':{'toolUse':{'input':'{}'}}}}
            yield {'contentBlockStop':{'contentBlockIndex':0}}
            yield {'messageStop':{'stopReason':'tool_use'}}
        yield {'metadata':{'usage':{'inputTokens':0,'outputTokens':0,'totalTokens':0},'metrics':{'latencyMs':0}}}
