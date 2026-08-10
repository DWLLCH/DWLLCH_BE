from .models import Policy


def get_policy_chatbot_answer(question: str, policy_id: int | None = None) -> str:
    """
    제도 전용 챗봇 질의에 대한 답변을 생성한다.
    TODO: 실제 AI API 연동으로 교체 예정 (지금은 임시 응답)
    """
    context = ""
    if policy_id:
        try:
            policy = Policy.objects.get(id=policy_id)
            context = f"[{policy.title}] {policy.content}"
        except Policy.DoesNotExist:
            context = ""

    # TODO: 여기서 외부 AI API(requests/httpx) 호출로 교체
    if context:
        return f"'{question}'에 대한 답변입니다. 관련 정책: {context[:100]}..."
    return f"'{question}'에 대한 일반적인 답변 준비 중입니다."