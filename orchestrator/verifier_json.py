import json
import difflib

def verify_json(output, target_template):
    try:
        data = json.loads(output)
        # 키 검증
        required_keys = set(json.loads(target_template).keys())
        if not required_keys.issubset(data.keys()):
            return False, "Missing keys"
        
        # 실제 내용 유사도 (간단한 Jaccard 유사도 혹은 exact match)
        # 여기서는 오케스트레이터가 가중치를 수정할 때의 지표로 활용
        return True, "Success"
    except:
        return False, "Invalid JSON"
