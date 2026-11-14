"""Assess GDTC/GDQP coursework against the student's own curriculum groups.

Zero-credit groups are checked by required course codes, never by summing
credits. English course completion does not establish an exit qualification.
"""
from app.core.hust_rules import GRADE_TO_SCALE4, PASSING_GRADES


def assess_non_credit_coursework(profile, curriculum):
    non_credit_ids = set(curriculum.get('non_credit_group_ids', []))
    course_map = {course['code']: course for course in curriculum.get('courses', [])}
    attempts = {}
    for course in profile.get('transcript', []):
        code = str(course.get('code', '')).upper().strip()
        grade = str(course.get('letter_grade', '')).upper().strip()
        if grade in GRADE_TO_SCALE4:
            attempts.setdefault(code, []).append(grade)
    results = {}
    for group in curriculum.get('groups', []):
        key = str(group.get('source_group_code', ''))
        if key not in {'220', '230'} or group['id'] not in non_credit_ids:
            continue
        codes = list(dict.fromkeys(group.get('course_codes', [])))
        # Refuse incomplete catalog groups rather than declaring success early.
        if not codes or len(codes) != group.get('course_count_reported'):
            continue
        records = []
        for code in codes:
            grades = attempts.get(code, [])
            grade = max(grades, key=GRADE_TO_SCALE4.__getitem__) if grades else None
            records.append({'course_code': code, 'course_name': course_map.get(code, {}).get('name', code),
                            'letter_grade': grade, 'is_passed': grade in PASSING_GRADES})
        passed = sum(row['is_passed'] for row in records)
        results[key] = {'status': 'completed' if passed == len(codes) else 'incomplete' if attempts else 'unverified',
                        'group_id': group['id'], 'source_group_code': key, 'name': group['name'],
                        'required_count': len(codes), 'passed_count': passed, 'records': records,
                        'missing_course_codes': [row['course_code'] for row in records if not row['is_passed']],
                        'source': 'coursework', 'note': 'Đối chiếu điểm chữ với các học phần trong nhóm CTĐT; ghi nhận hoàn thành học phần.'}
    return results


def with_coursework(section, profile, curriculum):
    coursework = assess_non_credit_coursework(profile, curriculum)
    if not coursework:
        return section
    return {**section, 'coursework': coursework, 'source_type': 'coursework',
            'status': 'synced', 'message': 'GDTC/GDQP được xét theo kết quả học phần trong CTĐT. Chuẩn tiếng Anh được đối chiếu riêng.',
            'synced_at': section.get('synced_at') or profile.get('school_sync', {}).get('synced_at')}
