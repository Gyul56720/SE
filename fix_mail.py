import house.report
from house import people
# owner를 유효한 객체로 전달하여 KeyError 방지
owner = people.BY_KEY['dv']
try:
    print(house.report.mail_body(owner, 'sub', [], [], attachment_name='test'))
except Exception as e:
    print(f"Error: {e}")
