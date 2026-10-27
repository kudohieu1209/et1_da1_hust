import os
import json
import re

def parse_ctt_html(raw_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    with open(raw_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Trích xuất thông tin sinh viên & chương trình đào tạo
    student_match = re.search(r'Chương trình\s*(\d+)\s*-\s*([^c]+)cho sinh viên\s*(\d+)\s*([^<]+)', content)
    student_info = {}
    if student_match:
        student_info = {
            'program_id': student_match.group(1).strip(),
            'program_name': student_match.group(2).strip().replace('&nbsp;', ' '),
            'student_id': student_match.group(3).strip(),
            'student_name': student_match.group(4).strip(),
        }

    # Bóc tách tất cả các hàng dữ liệu (dxgvDataRow)
    data_rows = re.findall(r'<tr[^>]*class=\"[^\"]*dxgvDataRow[^\"]*\"[^>]*>(.*?)</tr>', content, re.DOTALL)

    courses = []
    student_transcript = []

    for r in data_rows:
        tds = re.findall(r'<td([^>]*)>(.*?)</td>', r, re.DOTALL)
        cells = []
        for attrs, c in tds:
            is_checked = 'dxWeb_edtCheckBoxChecked' in c
            is_unchecked = 'dxWeb_edtCheckBoxUnchecked' in c
            text = re.sub(r'<[^>]+>', '', c).strip().replace('&nbsp;', '')
            if is_checked:
                cells.append(True)
            elif is_unchecked:
                cells.append(False)
            else:
                cells.append(text)
        
        # Cấu trúc cột của gvStudentProgram:
        # Col 0, 1: Khoảng đệm (indent)
        # Col 2: Mã HP (ETxxxx, MIxxxx...)
        # Col 3: Tên HP
        # Col 4: Kỳ học gợi ý
        # Col 5: Bắt buộc (checkbox True/False)
        # Col 6: TC Đào tạo
        # Col 7: TC đã học
        # Col 8: Mã HP thực tế học
        # Col 9: Ghi chú loại HP (Bắt buộc, Tự chọn, GDTC...)
        # Col 10: Điểm chữ (A, B+, B, C+, C, D+, D, F...)
        # Col 11: Điểm số (4.0, 3.5, 3.0...)
        # Col 12: Viện/Khoa
        if len(cells) >= 12:
            code = cells[2]
            name = cells[3]
            if code and len(code) >= 4 and not code.startswith('('):
                sem = cells[4]
                is_req = cells[5] if isinstance(cells[5], bool) else False
                credits_ctdt = cells[6]
                credits_taken = cells[7]
                actual_code = cells[8]
                cat = cells[9]
                letter = cells[10]
                num_grade = cells[11]
                dept = cells[12] if len(cells) > 12 else ''

                course_item = {
                    'code': code,
                    'name': name,
                    'suggested_semester': int(sem) if sem.isdigit() else None,
                    'is_compulsory': is_req,
                    'credits': float(credits_ctdt) if credits_ctdt.replace('.', '', 1).isdigit() else 0.0,
                    'category': cat,
                    'department': dept
                }

                if not any(c['code'] == code for c in courses):
                    courses.append(course_item)

                if letter:
                    # Deduplicate: Chỉ lưu 1 lần cho mỗi mã môn học
                    existing = next((t for t in student_transcript if t['code'] == code), None)
                    if not existing:
                        student_transcript.append({
                            'code': code,
                            'name': name,
                            'credits': float(credits_ctdt) if credits_ctdt.replace('.', '', 1).isdigit() else 0.0,
                            'letter_grade': letter,
                            'numeric_grade': float(num_grade) if num_grade.replace('.', '', 1).isdigit() else 0.0,
                            'is_passed': letter not in ['F']
                        })

    # Ghi file courses_et1.json
    courses_out = os.path.join(output_dir, 'courses_et1.json')
    with open(courses_out, 'w', encoding='utf-8') as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)

    # Ghi file student_profile.json
    student_profile = {
        'info': student_info,
        'total_courses_completed': len(student_transcript),
        'passed_courses': [c for c in student_transcript if c['is_passed']],
        'failed_courses': [c for c in student_transcript if not c['is_passed']],
        'transcript': student_transcript
    }
    profile_out = os.path.join(output_dir, 'student_profile.json')
    with open(profile_out, 'w', encoding='utf-8') as f:
        json.dump(student_profile, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] Trích xuất hoàn tất:")
    print(f" - Tổng số môn học trong CTĐT ET1: {len(courses)}")
    print(f" - Thông tin SV: {student_info.get('student_name')} - MSSV: {student_info.get('student_id')}")
    print(f" - Số môn SV đã hoàn thành: {len(student_transcript)}")

if __name__ == '__main__':
    raw = 'data/raw/et1_curiculum.html'
    out = 'data/processed'
    parse_ctt_html(raw, out)
