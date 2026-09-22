import os
import json
import re

def parse_hust_condition(cond_str: str):
    """
    Phân tích cú pháp điều kiện học phần chuẩn của CTT Bách Khoa:
    - '!' = Tiên quyết (bắt buộc qua điểm >= D)
    - '=' = Song hành (được phép học cùng kỳ)
    - Không dấu = Học trước (đã từng học / có điểm)
    - '/' = Phép HOẶC (chọn 1 trong các phương án)
    - ',' = Phép VÀ (bắt buộc thoả mãn tất cả trong phương án)
    """
    if not cond_str or not cond_str.strip():
        return []
    
    cond_str = cond_str.strip().replace('&nbsp;', '')
    if not cond_str:
        return []
    
    or_branches = cond_str.split('/')
    parsed_or_branches = []
    
    for branch in or_branches:
        branch = branch.strip()
        if not branch:
            continue
        
        # Nhận diện group modifier dạng (A, B)! hoặc (A, B)=
        group_modifier = None
        if branch.endswith('!') and '(' in branch:
            group_modifier = 'PREREQUISITE'
            branch = branch[:-1].strip()
        elif branch.endswith('=') and '(' in branch:
            group_modifier = 'COREQUISITE'
            branch = branch[:-1].strip()
        
        clean_branch = branch.replace('(', '').replace(')', '').strip()
        and_items = clean_branch.split(',')
        branch_reqs = []
        for item in and_items:
            item = item.strip()
            if not item:
                continue
            
            req_type = group_modifier or 'PRIOR'
            if item.endswith('!'):
                req_type = 'PREREQUISITE'
                code = item[:-1]
            elif item.endswith('='):
                req_type = 'COREQUISITE'
                code = item[:-1]
            else:
                code = item
            
            code = code.strip()
            if code:
                branch_reqs.append({
                    'code': code,
                    'type': req_type
                })
        if branch_reqs:
            parsed_or_branches.append(branch_reqs)
    
    return parsed_or_branches

def merge_conditions():
    curriculum_path = 'project/data/processed/courses_et1.json'
    raw_cond_path = 'project/data/raw/ctt_et_conditions.json'
    output_path = 'project/data/processed/prerequisites_et1.json'

    with open(curriculum_path, 'r', encoding='utf-8') as f:
        et1_courses = json.load(f)

    ctt_data = []
    if os.path.exists(raw_cond_path):
        with open(raw_cond_path, 'r', encoding='utf-8') as f:
            ctt_data = json.load(f)

    ctt_map = {item['code']: item for item in ctt_data if 'code' in item}
    print(f"Tổng số môn từ CTT cào về: {len(ctt_map)}")
    print(f"Tổng số môn trong CTĐT ET1 chuẩn: {len(et1_courses)}")

    merged = []
    matched_count = 0

    for c in et1_courses:
        code = c['code']
        ctt_info = ctt_map.get(code)
        
        raw_condition = ''
        if ctt_info:
            raw_condition = ctt_info.get('condition', '').strip()
            matched_count += 1
        
        # Parse chuỗi điều kiện thành các nhánh logic OR / AND
        condition_tree = parse_hust_condition(raw_condition)

        # Trích xuất danh sách phẳng các môn tiên quyết, học trước, song hành (để tiện truy vấn)
        flat_prereqs = set()
        flat_priors = set()
        flat_cores = set()

        for branch in condition_tree:
            for item in branch:
                if item['type'] == 'PREREQUISITE':
                    flat_prereqs.add(item['code'])
                elif item['type'] == 'COREQUISITE':
                    flat_cores.add(item['code'])
                else:
                    flat_priors.add(item['code'])

        merged.append({
            'code': code,
            'name': c['name'],
            'suggested_semester': c.get('suggested_semester'),
            'credits': c.get('credits', 0),
            'is_compulsory': c.get('is_compulsory', False),
            'category': c.get('category', ''),
            'raw_condition': raw_condition,
            'condition_tree': condition_tree,
            'flat_prerequisites': sorted(list(flat_prereqs)),
            'flat_prior_courses': sorted(list(flat_priors)),
            'flat_corequisites': sorted(list(flat_cores)),
            'min_credits_accumulated': 120 if '4900' in code else (90 if '3290' in code else 0)
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✅ ĐÃ HỢP NHẤT THÀNH CÔNG VÀO {output_path}:")
    print(f" - Tổng số môn ngành ET1 được xử lý: {len(merged)}")
    print(f" - Số môn khớp chính xác với CTT: {matched_count}")

if __name__ == '__main__':
    merge_conditions()
