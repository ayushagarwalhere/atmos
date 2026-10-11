import json
from strands.models import BedrockModel
from . import cloud_budget

class BudgetBedrockModel(BedrockModel):
    async def stream(self,messages,tool_specs=None,system_prompt=None,**kwargs):
        config = self.get_config()
        max_output = config.get('max_tokens') or 512
        payload = json.dumps({'messages':messages,'tools':tool_specs,'system':system_prompt,
            'system_content':kwargs.get('system_prompt_content'),'tool_choice':kwargs.get('tool_choice')},ensure_ascii=False).encode()
        reservation = cloud_budget.inference_reservation(len(payload),max_output)
        cloud_budget.reserve('bedrock',reservation)
        async for event in super().stream(messages,tool_specs,system_prompt,**kwargs):
            yield event
