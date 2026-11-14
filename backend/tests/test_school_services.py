import copy
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.auth import runtime
from app.auth.passwords import hash_password
from app.auth.service import AuthService
from app.auth.store import MongoAuthStore
from app.core.hust_rules import assess_academic_warning
from app.main import app
from app.services.ctt_sections import completion, number, parse_section, parse_requirements, normalize_saved_section, parse_warning_level
from app.services.data_loader import data_loader
from app.services.exam_import import preview_exam_pdf
from app.services.profile_repository import MongoProfileRepository
from app.services.school_account_service import complete_school_login
from app.services.school_portal import _collect_school_services
from app.services.non_credit_coursework import assess_non_credit_coursework
from tests.test_school_login import snapshot
from testing_support import isolated_database, sample_profiles

STAMP = "2026-11-15T00:00:00+00:00"
ROOT = "https://ctt-sis.hust.edu.vn/"


def table(headers, rows, grid="gvResults_DXMainTable"):
    header = "".join(f"<th>{x}</th>" for x in headers)
    data = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
    return f'<table id="{grid}"><tr>{header}</tr>{data}</table>'


ENGLISH = table(["Ngày thi", "Điểm nghe", "Điểm đọc", "Tổng điểm"], [["15/10/2026", "420", "400", "820"]])
TIMETABLE = table(["Mã HP", "Tên HP", "Mã lớp", "Thứ", "Tiết", "Phòng", "Tuần"], [["ET2030", "Lập trình", "123456", "CN", "1-3", "D3-201", "1-16"]])
TUITION = table(["Học kỳ", "Phải nộp", "Đã nộp", "Còn nợ"], [["2026.1", "9.850.000", "9.000.000", "850.000"]])
CLASSMATES = table(["MSSV", "Họ và tên", "Lớp"], [["20221235", "Sinh viên tổng hợp", "Lớp thử - K67"]])
REQUIREMENTS = '''<table><tr><td>Mức cảnh báo học tập</td><td>0</td></tr>
<tr><td>Chứng chỉ GDTC</td><td>Đạt</td></tr><tr><td>Chứng chỉ GDQP-AN</td><td>Chưa đạt</td></tr>
<tr><td>Chuẩn đầu ra tiếng Anh</td><td>Đã hoàn thành</td></tr></table>'''


class SchoolSectionParserTests(unittest.TestCase):
    def test_real_ctt_m_prefix_warning_and_existing_evidence(self):
        for value, expected in [('M0',0),('M1',1),('M2',2),('M3',3),('Mức 0',0),('Mức cảnh báo M1',None),('M4',None),('2026.1 M0',None)]:
            self.assertEqual(parse_warning_level(value), expected, value)
        parsed = parse_requirements('<p>Mức cảnh báo: <span>M0</span></p>')
        self.assertEqual(parsed['warning_level'],0)
        old = {'status':'unavailable', 'warning_level':None,'synced_at':STAMP,'evidence':[{'label':'Mức cảnh báo ','value':'M0'}]}
        fixed = normalize_saved_section('warning',old)
        self.assertEqual((fixed['status'],fixed['warning_level'],fixed['synced_at']),('synced',0,STAMP))
        self.assertIsNone(old['warning_level'])
        conflicting = {**old,'evidence':old['evidence']+[{'label':'Mức cảnh báo','value':'M1'}]}
        self.assertIsNone(normalize_saved_section('warning',conflicting)['warning_level'])

    def test_zero_credit_coursework_requires_every_catalog_course_and_keeps_english_separate(self):
        curriculum = {'non_credit_group_ids':['group_220','group_230','group_240'], 'courses':[], 'groups':[
            {'id':'group_220','source_group_code':'220','name':'GDTC','course_count_reported':2,'course_codes':['PE1014','PE1024']},
            {'id':'group_230','source_group_code':'230','name':'GDQP','course_count_reported':4,'course_codes':['MIL1210','MIL1220','MIL1230','MIL1240']},
            {'id':'group_240','source_group_code':'240','name':'Tiếng Anh','course_count_reported':2,'course_codes':['FL1131','FL1132']},
        ]}
        transcript = [{'code':code,'letter_grade':grade,'credits':0} for code,grade in [
            ('PE1014','B'),('PE1024','B+'),('MIL1210','C'),('MIL1220','D'),('MIL1230','C'),('MIL1240','B'),('FL1131','C'),('FL1132','C')]]
        profile = {'transcript':transcript}
        before = copy.deepcopy(profile)
        result = assess_non_credit_coursework(profile,curriculum)
        self.assertEqual(result['220']['status'],'completed')
        self.assertEqual((result['230']['passed_count'],result['230']['required_count']),(4,4))
        self.assertNotIn('240',result)
        self.assertEqual(profile,before)
        # Passing an unrelated elective does not replace a missing catalog course.
        profile['transcript'] = transcript[:1]+[{'code':'PE2401','letter_grade':'A'}]
        partial = assess_non_credit_coursework(profile,curriculum)['220']
        self.assertEqual(partial['status'],'incomplete')
        self.assertEqual(partial['missing_course_codes'],['PE1024'])
        # An earlier failure is resolved by a recorded passing attempt.
        profile['transcript'] = transcript+[{'code':'PE1024','letter_grade':'F','is_passed':True}]
        self.assertEqual(assess_non_credit_coursework(profile,curriculum)['220']['status'],'completed')
        profile['transcript'] = [{'code':'PE1014','letter_grade':'F','is_passed':True}]
        self.assertEqual(assess_non_credit_coursework(profile,curriculum)['220']['passed_count'],0)
        profile['transcript'] = []
        self.assertEqual(assess_non_credit_coursework(profile,curriculum)['220']['status'],'unverified')
        curriculum['groups'][0]['course_count_reported'] = 3
        self.assertNotIn('220',assess_non_credit_coursework(profile,curriculum))

    def test_actual_ctt_columns_and_saved_tables_are_normalized(self):
        html = table(['Điểm nghe', 'Điểm đọc', 'Điểm viết', 'Điểm nói', 'Điểm tổng'], [['100','150','80','90','420']])
        english = parse_section('english', html, ROOT, STAMP)['records'][0]
        self.assertEqual((english['score'], english['writing'], english['speaking']), (420,80,90))
        raw = {'status':'partial', 'synced_at': STAMP, 'tables':[{'headers':['Mã SV','Họ','Đệm','Tên','Tên lớp'], 'rows':[['20221235','Nguyễn','Văn','Bình','ET1-01']]}]}
        normalized = normalize_saved_section('classmates', raw)
        self.assertEqual(normalized['records'][0]['student_name'], 'Nguyễn Văn Bình')
        self.assertEqual(normalized['records'][0]['class_name'], 'ET1-01')
        self.assertEqual(normalized['synced_at'], STAMP)
        self.assertNotIn('records', raw)

    def test_actual_tuition_charges_are_not_mislabeled_as_debt(self):
        html = table(['Mã HP','Tên HP','Tổng tiền học phần'], [['ET2030','Lập trình','2,800,000 đ']])
        html += table(['Loại tiền','Số tiền','Hệ số đóng','Thực đóng','Ngày cập nhật'], [['Học phí theo đăng ký học tập','2,800,000 đ','1','2,800,000 đ','09.10.2026 09:12']])
        parsed = parse_section('tuition', html, ROOT, STAMP)
        self.assertEqual(parsed['status'], 'synced')
        self.assertEqual(parsed['charges'][0]['amount'], 2800000)
        self.assertEqual(parsed['payments'][0]['actual_amount'], 2800000)
        self.assertEqual(parsed['records'], [])

    def test_actual_clock_and_combined_day_column(self):
        html = table(['Mã HP','Tên lớp','Thời gian','Phòng học'], [['ET2030','Lập trình','Thứ 2,15h5 - 17h30','D3-201']])
        parsed = parse_section('timetable', html, ROOT, STAMP)
        self.assertEqual(parsed['records'][0]['day_of_week'], 2)
        self.assertIsNone(parsed['records'][0]['start_period'])
        self.assertEqual(parsed['records'][0]['course_name'], 'Lập trình')

    def test_adjacent_profile_labels_and_discovery(self):
        import threading
        details = '<p>Mức cảnh báo học tập</p><span>1</span><p>Chứng chỉ GDTC</p><span>Đạt</span>'
        self.assertEqual(parse_requirements(details)['warning_level'], 1)
        def fetch(page, url):
            return {'url': url, 'html': details if url.endswith('Profile.aspx') else '<p>Không có dữ liệu</p>'}
        with mock.patch('app.services.school_portal._fetch_ctt_html', side_effect=fetch) as fetcher:
            sections = _collect_school_services(object(), [(ROOT, '<a href="/Students/Exams.aspx">Lịch thi</a><a href="/Students/Profile.aspx">Thông tin cá nhân</a>')], threading.Event())
        self.assertTrue(any(x.args[1].endswith('Profile.aspx') for x in fetcher.call_args_list))
        self.assertEqual(sections['warning']['warning_level'], 1)
        self.assertEqual(sections['certificates']['requirements']['220'], 'completed')

    def test_toeic_history_is_read_without_assuming_a_graduation_threshold(self):
        parsed = parse_section("english", ENGLISH, ROOT, STAMP)
        self.assertEqual(parsed["status"], "synced")
        self.assertEqual(parsed["records"][0]["score"], 820)
        self.assertEqual(parsed["records"][0]["test_date"], "2026-10-15")
        self.assertNotIn("is_qualified", parsed)

    def test_zero_scores_and_zero_debt_are_preserved(self):
        self.assertEqual(number("0"), 0)
        self.assertEqual(number("9.850.000 VNĐ"), 9850000)
        self.assertIsNone(number("Chưa có dữ liệu"))
        english = parse_section("english", table(["Ngày thi", "Điểm"], [["15/10/2026", "0"]]), ROOT, STAMP)
        self.assertEqual(english["records"][0]["score"], 0)

    def test_sunday_and_temporary_timetable_are_not_lost(self):
        item = parse_section("temporary_timetable", TIMETABLE, ROOT, STAMP)["records"][0]
        self.assertEqual(item["day_of_week"], 8)
        self.assertEqual((item["start_period"], item["end_period"]), (1, 3))
        self.assertTrue(item["is_temp"])

    def test_clock_text_is_not_mistaken_for_class_periods(self):
        parsed = parse_section("timetable", TIMETABLE.replace("1-3", "06:45 - 09:10"), ROOT, STAMP)
        self.assertEqual(parsed["records"], [])
        self.assertEqual(parsed["status"], "partial")
        self.assertTrue(parsed["tables"])

    def test_tuition_uses_real_amounts_and_does_not_duplicate_the_total_row(self):
        html = TUITION.replace('</table>', '<tr><td>Tổng</td><td>9.850.000</td><td>9.000.000</td><td>850.000</td></tr></table>')
        parsed = parse_section("tuition", html, ROOT, STAMP)
        self.assertEqual(len(parsed["records"]), 1)
        self.assertEqual(parsed["records"][0]["debt"], 850000)

    def test_empty_table_is_distinct_from_an_unknown_page(self):
        self.assertEqual(parse_section("english", table(["Ngày thi", "Điểm"], []), ROOT, STAMP)["status"], "empty")
        self.assertEqual(parse_section("english", '<p>Trang không có bảng phù hợp</p>', ROOT, STAMP)["status"], "unavailable")

    def test_unknown_columns_are_retained_instead_of_inventing_values(self):
        section = parse_section("english", table(["Cột mới", "Một cột khác"], [["A", "B"]]), ROOT, STAMP)
        self.assertEqual(section["status"], "partial")
        self.assertEqual(section["records"], [])
        self.assertEqual(section["tables"][0]["rows"], [["A", "B"]])

    def test_paginated_data_is_marked_partial(self):
        html = ENGLISH + '<a class="dxp-num">1</a><a class="dxp-num">2</a>'
        self.assertEqual(parse_section("english", html, ROOT, STAMP)["status"], "partial")

    def test_certificates_and_warning_are_taken_only_from_explicit_labels(self):
        parsed = parse_requirements(REQUIREMENTS)
        self.assertEqual(parsed["warning_level"], 0)
        self.assertEqual(parsed["requirements"], {"220": "completed", "230": "incomplete", "240": "completed"})
        self.assertEqual(completion("Chưa đạt"), "incomplete")
        self.assertEqual(completion("Đang xử lý"), "unverified")
        not_certificates = table(["Mã HP", "Tên HP", "Điểm"], [["PE1110", "Giáo dục thể chất", "A"], ["MIL1110", "GDQP", "B"]])
        self.assertTrue(all(x == "unverified" for x in parse_requirements(not_certificates)["requirements"].values()))

    def test_multiple_warning_levels_are_not_guessed(self):
        html = REQUIREMENTS + '<table><tr><td>Mức cảnh báo học tập</td><td>2</td></tr></table>'
        self.assertIsNone(parse_requirements(html)["warning_level"])

    def test_read_only_certificate_checkboxes_and_explicit_status_images(self):
        html = '''<table><tr><td>Chứng chỉ GDTC</td><td><input type="checkbox" disabled checked></td></tr>
        <tr><td>Chứng chỉ GDQP</td><td><input type="checkbox" disabled></td></tr>
        <tr><td>Chuẩn đầu ra tiếng Anh</td><td><img alt="Đạt"></td></tr></table>'''
        self.assertEqual(parse_requirements(html)['requirements'], {'220': 'completed', '230': 'incomplete', '240': 'completed'})

    def test_exam_columns_and_classmate_rows_are_extracted(self):
        exams = table(["Mã HP", "Tên HP", "Ngày thi", "Giờ thi", "Phòng"], [["ET2030", "Lập trình", "15/12/2026", "07:30", "D3-201"]])
        self.assertEqual(parse_section("exams", exams, ROOT, STAMP)["records"][0]["exam_date"], "2026-12-15")
        self.assertEqual(parse_section("classmates", CLASSMATES, ROOT, STAMP)["records"][0]["student_id"], "20221235")

    def test_collector_isolates_optional_errors_and_keeps_core_identity_pages(self):
        import threading
        def fetch(page, url):
            if url.endswith('CheckTuition.aspx'):
                raise RuntimeError("never-log-this-token")
            html = ENGLISH if url.endswith('ToeicMarks.aspx') else REQUIREMENTS if url.endswith('StudentProgram.aspx') else TIMETABLE
            return {"url": url, "html": html, "status": 200}
        with mock.patch('app.services.school_portal._fetch_ctt_html', side_effect=fetch):
            sections = _collect_school_services(object(), [(ROOT, REQUIREMENTS)], threading.Event())
        self.assertEqual(sections['english']['records'][0]['score'], 820)
        self.assertEqual(sections['tuition']['status'], 'error')
        self.assertNotIn('token', sections['tuition']['message'])
        self.assertEqual(sections['warning']['warning_level'], 0)
        self.assertEqual(sections['certificates']['requirements']['220'], 'completed')
        self.assertEqual(sections['exams']['status'], 'unavailable')

    def test_pdf_preview_requires_text_and_a_reviewable_exam_row(self):
        with self.assertRaises(ValueError):
            preview_exam_pdf(b'not a pdf')
        fake = mock.MagicMock()
        fake.is_encrypted = False
        fake.pages = [mock.MagicMock()]
        fake.pages[0].extract_text.return_value = 'ET2030  Lập trình  123456  15/12/2026  07:30  D3-201  Tự luận'
        with mock.patch('pypdf.PdfReader', return_value=fake):
            rows = preview_exam_pdf(b'%PDF-fixture')
        self.assertEqual(rows[0]['exam_date'], '2026-12-15')
        self.assertEqual(rows[0]['class_code'], '123456')
        self.assertEqual(rows[0]['room'], 'D3-201')


class SchoolServiceApiTests(unittest.TestCase):
    def setUp(self):
        db = isolated_database()
        self.profiles = MongoProfileRepository(db)
        self.auth = AuthService(MongoAuthStore(db), self.profiles)
        for sid in ('20220001', '20231890'):
            self.profiles.save(sid, sample_profiles()[sid])
            self.auth.store.create_user({'student_id': sid, 'password_hash': hash_password('test-service-password'), 'created_at': self.auth.clock()})
        for patcher in (mock.patch.object(data_loader, '_profiles', self.profiles), mock.patch.object(runtime, 'auth_service', self.auth)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.client.post('/api/auth/login', json={'student_id': '20220001', 'password': 'test-service-password'})

    def test_unconnected_accounts_do_not_receive_fake_scores_fees_or_classes(self):
        english = self.client.get('/api/student/toeic')
        self.assertEqual(english.status_code, 200, english.text)
        self.assertIsNone(english.json()['score'])
        self.assertIsNone(english.json()['required_score'])
        self.assertIsNone(english.json()['is_qualified'])
        tuition = self.client.get('/api/student/tuition').json()
        self.assertIsNone(tuition['current_debt'])
        self.assertEqual(tuition['semesters'], [])
        self.assertEqual(self.client.get('/api/student/timetable').json()['items'], [])
        self.assertEqual(self.client.get('/api/student/exams').json()['exams'], [])
        self.assertEqual(self.client.get('/api/student/classmates').json()['students'], [])
        self.assertEqual(TestClient(app).get('/api/student/school-services').status_code, 401)

    def test_services_are_scoped_to_the_authenticated_student(self):
        mine = self.profiles.get('20220001')
        mine['school_services'] = {'english': parse_section('english', ENGLISH, ROOT, STAMP), 'classmates': parse_section('classmates', CLASSMATES, ROOT, STAMP)}
        self.profiles.save('20220001', mine)
        other = self.profiles.get('20231890')
        other['school_services'] = {'english': {'status': 'synced', 'records': [{'score': 100}]}}
        self.profiles.save('20231890', other)
        result = self.client.get('/api/student/toeic', headers={'X-Student-ID': '20231890'}).json()
        self.assertEqual(result['score'], 820)
        self.assertEqual(self.client.get('/api/student/classmates?class_code=not-my-class').status_code, 404)

    def test_school_sync_updates_real_warning_and_certificates_without_affecting_other_students(self):
        before = self.profiles.get('20231890')
        data = snapshot('20220001')
        assessment = parse_section('requirements', REQUIREMENTS.replace('<td>0</td>', '<td>M0</td>'), ROOT, STAMP)
        data.services = {'english': parse_section('english', ENGLISH, ROOT, STAMP), 'warning': assessment, 'certificates': assessment}
        complete_school_login(self.auth, data, 'ET1', '20220001')
        mine = self.profiles.get('20220001')
        self.assertEqual(mine['info']['warning_level'], 0)
        self.assertEqual(mine['info']['warning_source'], 'ctt')
        self.assertEqual(mine['non_credit_status']['220'], 'completed')
        self.assertEqual(mine['non_credit_status']['230'], 'incomplete')
        self.assertIn('đồng bộ trực tiếp', assess_academic_warning(mine)['basis'])
        self.assertEqual(self.profiles.get('20231890'), before)
        audit = self.client.get('/api/student/audit').json()
        physical = next(row for row in audit['non_credit_requirements'] if row['requirement_id'] == '220')
        self.assertEqual(physical['source'], 'ctt')

    def test_services_and_audit_use_same_coursework_for_owner_without_claiming_issuance(self):
        mine = self.profiles.get('20220001')
        other = copy.deepcopy(self.profiles.get('20231890'))
        mine['non_credit_status'] = {}
        mine['transcript'] = [{'code':code,'name':code,'credits':0,'letter_grade':'D','is_passed':True} for code in ['PE1014','PE1024','MIL1210','MIL1220','MIL1230','MIL1240']]
        mine['passed_courses'] = copy.deepcopy(mine['transcript'])
        mine['failed_courses'] = []
        self.profiles.save('20220001',mine)
        services = self.client.get('/api/student/school-services').json()['sections']['certificates']
        self.assertEqual(services['source_type'],'coursework')
        self.assertEqual(services['coursework']['220']['passed_count'],2)
        self.assertEqual(services['coursework']['230']['status'],'completed')
        self.assertNotIn('240',services['coursework'])
        self.assertNotEqual(services.get('requirements',{}).get('220'),'completed')
        audit = self.client.get('/api/student/audit').json()
        for key in ['220','230']:
            row = next(item for item in audit['non_credit_requirements'] if item['requirement_id']==key)
            self.assertEqual((row['status'],row['source']),('completed','coursework'))
        self.assertEqual(self.profiles.get('20231890'),other)

    def test_failed_optional_refresh_retains_previous_values_as_stale(self):
        data = snapshot('20220001')
        data.services = {'english': parse_section('english', ENGLISH, ROOT, STAMP)}
        complete_school_login(self.auth, data, 'ET1', '20220001')
        second = snapshot('20220001')
        second.services = {'english': {'status': 'error', 'synced_at': '2026-11-16T00:00:00Z', 'records': [], 'tables': [], 'message': 'Chưa cập nhật được'}}
        complete_school_login(self.auth, second, 'ET1', '20220001')
        section = self.profiles.get('20220001')['school_services']['english']
        self.assertEqual(section['status'], 'stale')
        self.assertEqual(section['records'][0]['score'], 820)
        self.assertEqual(section['last_attempt_at'], '2026-11-16T00:00:00Z')

    def test_pdf_preview_does_not_mutate_profile_and_import_only_touches_owner(self):
        before = copy.deepcopy(self.profiles.get('20220001'))
        record = {'course_code': 'ET2030', 'course_name': 'Lập trình', 'exam_date': '2026-12-15', 'exam_time': '07:30', 'room': 'D3-201'}
        with mock.patch('app.services.exam_import.preview_exam_pdf', return_value=[record]):
            result = self.client.post('/api/student/exams/preview', files={'file': ('fixture.pdf', b'%PDF-fixture', 'application/pdf')})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.profiles.get('20220001'), before)
        saved = self.client.post('/api/student/exams/import', json={'exams': [record]})
        self.assertEqual(saved.status_code, 200, saved.text)
        section = self.profiles.get('20220001')['school_services']['exams']
        self.assertEqual(section['source_type'], 'imported_pdf')
        self.assertEqual(len(section['records']), 1)
        self.assertNotIn('school_services', self.profiles.get('20231890'))
        invalid = {**record, 'exam_date': '2026-02-30'}
        self.assertEqual(self.client.post('/api/student/exams/import', json={'exams': [invalid]}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
