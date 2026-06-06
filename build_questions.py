import json
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "기출문제"
OUT_DIR = ROOT / "ocr_images"
OCR_RESULTS_DIR = ROOT / "ocr_results"
SAMPLES_DIR = ROOT / "samples"
OUT_JSON = ROOT / "questions.json"
OUT_DATA_JS = ROOT / "data.js"
EXCEL_PATH = ROOT / "정답표" / "정답표.xlsx"

# Reconfigure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Pre-populated Korean explanations for 2018 and 2019 Java Programming questions
EXPLANATIONS = {
    "2018": {
        36: "Eclipse for JavaScript는 자바 개발(JDK, JVM 등)을 위해 필수적인 도구가 아닙니다. 자바 프로그램 실행 및 개발에는 JDK, JVM, JRE 등이 핵심 요소입니다.",
        37: "배열 선언 이후 초기화할 때는 'c = {1, 2, 3, 4};' 와 같이 단독으로 사용할 수 없으며, 'c = new int[]{1, 2, 3, 4};' 형식으로 지정해야 합니다.",
        38: "두 변수 i와 j 사이에 공백을 포함하여 출력하기 위해서는 'i + \" \" + j' 형태로 문자열 결합을 수행해야 합니다.",
        39: "자바는 단일 상속(extends Class)과 다중 인터페이스 구현(implements Interface1, Interface2...)을 지원하므로 'class A extends B implements Y, Z'가 올바른 구조입니다.",
        40: "메소드 오버라이딩 시 매개변수와 반환 타입이 동일해야 하며, 접근 제어자는 부모 클래스의 메소드보다 같거나 넓은 범위를 가져야 합니다. (protected인 compute 메소드는 protected 또는 public으로 재정의 가능하므로 a, b 모두 가능)",
        41: "인터페이스나 클래스를 상속받아 이름 없이 정의하는 동시에 객체를 생성하는 구문으로, 'CSuper 클래스를 상속받는 익명 클래스를 정의하고 동시에 객체를 생성한다'가 맞습니다.",
        42: "컴파일 시 외부 클래스(CSuper), 메인 클래스(AnonymousTest), 그리고 익명 클래스(AnonymousTest$1)가 각각 .class 파일로 생성되므로 총 3개의 클래스 파일이 생성됩니다.",
        43: "추상 클래스(abstract class)는 직접 객체(인터페이스와 마찬가지로 new를 통한 인스턴스)를 생성할 수 없습니다. 따라서 '추상 클래스는 인스턴스를 생성시킬 수 있다'는 설명은 잘못되었습니다.",
        44: "자바의 제네릭(Generic) 타입 매개변수에는 기본 자료형(int, double 등)을 사용할 수 없으며, 반드시 래퍼 클래스(Integer, Double 등) 객체 타입을 사용해야 합니다.",
        45: "str1과 str2는 동일한 인스턴스를 가리키므로 참조 비교(==) 결과가 true입니다. 반면 str3은 new 키워드로 새로운 인스턴스를 생성했으므로 'str2 == str3'는 참조 주소가 달라 false를 반환합니다.",
        46: "자바의 String 클래스는 불변(immutable) 객체이므로 문자열이 자주 수정되는 프로그램에서는 성능 저하를 방지하기 위해 가변 객체인 StringBuffer 또는 StringBuilder를 사용하는 것이 좋습니다.",
        47: "바이트 단위로 파일 입력을 처리하는 대표적인 입력 스트림 클래스는 FileInputStream입니다. FileReader는 문자 단위 입력 스트림입니다.",
        48: "NIO에서 'fileChannel.read(buffer)' 메소드는 파일 채널로부터 데이터를 읽어서 인자로 전달된 buffer에 기록하는 역할을 수행합니다.",
        49: "자바 컬렉션 프레임워크 중 순서를 유지하지 않고 중복을 허용하지 않는 자료구조 인터페이스는 Set입니다.",
        50: "Map 인터페이스는 키(Key)와 값(Value)의 쌍으로 저장되므로 제네릭 선언 시 'Map<String, Type>'과 같이 두 개의 타입 매개변수를 지정해야 합니다.",
        51: "Thread.yield() 메소드는 현재 실행 중인 스레드가 동일한 우선순위를 가진 다른 스레드에게 CPU 제어권을 양보하도록 유도합니다.",
        52: "join() 메소드는 해당 스레드가 종료될 때까지 호출한 스레드(여기서는 메인 스레드)를 대기(waiting) 상태로 만들어 결과적으로 메인 스레드의 'finished' 출력이 가장 마지막에 실행됩니다.",
        53: "Thread의 join() 호출은 InterruptedException 예외를 발생시킬 수 있으므로 메소드 선언부에 'throws InterruptedException'을 추가하여 예외 처리를 전달해야 합니다.",
        54: "AWT에서 여러 항목 중 하나를 선택할 수 있도록 해주는 드롭다운 형태의 컴포넌트는 Choice 클래스입니다.",
        55: "List 컴포넌트에서 특정 항목을 마우스로 싱글 클릭하면 ItemEvent가 발생하고, 더블 클릭하면 ActionEvent가 발생합니다.",
        56: "화면에 배치된 컴포넌트들이 2행 3열의 바둑판 형태로 균일하게 정렬된 것은 GridLayout 배치 관리자를 사용한 것입니다.",
        57: "이벤트 핸들러인 WindowAdapter는 클래스이므로 상속받기 위해 'extends WindowAdapter'를 사용해야 합니다. (WindowListener는 인터페이스이므로 implements 구현이 필요함)",
        58: "프레임에 윈도우 이벤트 리스너를 등록하는 메소드는 addWindowListener()이며, 객체를 생성해 인자로 넘겨주어야 합니다.",
        59: "주어진 세 문장은 순서대로 1. 데이터베이스 연결 수립(getConnection), 2. SQL 질의 작성을 위한 Statement 객체 생성(createStatement), 3. SQL 실행 및 결과 반환(executeQuery) 단계를 나타냅니다.",
        60: "JDBC에서 SELECT 쿼리 질의 결과를 담아 반환하는 executeQuery() 메소드의 반환 객체 타입은 ResultSet입니다."
    },
    "2019": {
        36: "Java 파일 컴파일 시 바이트코드 형태로 생성되는 실행 파일의 확장자는 '.class'입니다.",
        37: "자바 가상 머신(JVM)은 바이트코드로 된 프로그램(.class 파일)을 실행시키는 자바 플랫폼의 핵심 구성 요소입니다.",
        38: "main 메소드의 시그니처는 반드시 'public static void main(String[] args)' 형식이어야 합니다. 매개변수명은 달라도 되나 String 배열 타입은 필수적입니다.",
        39: "정수(int)형과 실수(double)형 연산 시, 정수형 변수가 실수형으로 자동 타입 변환(promotion)되어 연산이 수행됩니다.",
        40: "클래스 내에서 인스턴스 변수와 메소드는 객체를 생성(new)한 후에만 사용할 수 있지만, static이 붙은 클래스(정적) 변수와 정적 메소드는 객체 생성 없이 사용할 수 있습니다.",
        41: "생성자(Constructor)는 객체 생성 시 new 구문에 의해 호출되며, 부모 클래스의 생성자를 명시적으로 호출할 때는 super() 키워드를 첫 줄에 사용해야 합니다.",
        42: "클래스 A가 클래스 B를 상속받는 구문은 'class A extends B'로 표현됩니다.",
        43: "메소드 오버로딩(Overloading)은 동일한 메소드 이름을 사용하되 매개변수의 개수나 타입을 다르게 하여 정의하는 기법입니다.",
        44: "가시성(접근 제어)이 가장 좁은 것부터 넓은 순서대로 정렬하면 private -> default(package) -> protected -> public 순입니다.",
        45: "추상 클래스(abstract class)는 추상 메소드를 포함할 수 있는 클래스로, 단독으로 인스턴스화(객체 생성)할 수 없고 반드시 서브클래스에서 상속받아 오버라이딩해야 합니다.",
        46: "자바에서 모든 클래스의 최상위 부모 클래스는 java.lang.Object 클래스입니다.",
        47: "자바 예외 처리에서 예외 발생 여부와 상관없이 무조건 실행해야 하는 코드 블록은 finally 블록입니다.",
        48: "자바의 문자열 클래스 중 String은 한번 생성되면 변하지 않는 불변(immutable) 클래스이며, StringBuffer와 StringBuilder는 가변(mutable) 클래스입니다.",
        49: "문자 단위 파일 입력을 처리하기 위해 사용되는 스트림 클래스는 FileReader입니다. FileInputStream은 바이트 단위 입력에 사용됩니다.",
        50: "NIO의 버퍼(Buffer) 속성 중 버퍼에 저장할 수 있는 최대 데이터 개수를 의미하는 것은 capacity입니다.",
        51: "자바에서 새로운 독립적 실행 흐름(스레드)을 만들기 위해 구현해야 하는 대표적인 인터페이스는 Runnable 인터페이스입니다.",
        52: "스레드의 상태 중 실행 대기 상태에서 CPU를 할당받아 실행되는 상태로 전이하는 과정을 디스패치(Dispatch)라고 합니다.",
        53: "스레드가 실행되는 핵심 로직을 오버라이딩하는 Runnable 인터페이스의 메소드는 run() 메소드입니다.",
        54: "AWT GUI에서 마우스 클릭 등의 버튼 컴포넌트에서 이벤트 발생 시 동작을 처리하기 위해 구현해야 하는 이벤트 리스너 인터페이스는 ActionListener입니다.",
        55: "여러 컴포넌트를 카드처럼 겹쳐두고 특정 시점에 하나의 카드만 보여주도록 관리하는 AWT 배치 관리자는 CardLayout입니다.",
        56: "자바 GUI에서 화면의 그래픽을 다시 그리도록 요청할 때 내부적으로 paint() 메소드를 호출하는 메소드는 repaint()입니다.",
        57: "메소드 내에 임시로 정의하여 해당 메소드 안에서만 사용하는 클래스를 로컬 클래스(Local Class)라고 부릅니다.",
        58: "데이터베이스 연결, 질의문 실행 등 자바 프로그램에서 관계형 데이터베이스(RDBMS)에 접속할 수 있도록 해주는 표준 API는 JDBC입니다.",
        59: "JDBC를 통해 데이터베이스에 연결하기 위해 가장 먼저 필요한 객체 연결 과정은 DriverManager.getConnection()을 사용하는 것입니다.",
        60: "디지털 포렌식이나 증거물 수집 시 원본 파일의 훼손 여부를 확인하기 위해 데이터 무결성 검증용 해시값을 연산하는 대표적인 해시 알고리즘은 SHA-256 등입니다."
    }
}

# --- Excel Parser Functions ---
def get_xlsx_shared_strings(z):
    try:
        sst_xml = z.read("xl/sharedStrings.xml")
        root = ET.fromstring(sst_xml)
        ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        strings = []
        for t in root.findall(".//ns:t", ns):
            strings.append(t.text)
        return strings
    except KeyError:
        return []

def get_xlsx_sheets(z):
    wb_xml = z.read("xl/workbook.xml")
    root = ET.fromstring(wb_xml)
    ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    sheets = []
    for sheet in root.findall(".//ns:sheet", ns):
        name = sheet.attrib.get("name")
        sheet_id = sheet.attrib.get("sheetId")
        r_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        sheets.append((name, sheet_id, r_id))
    return sheets

def parse_sheet(z, r_id, shared_strings):
    rels_xml = z.read("xl/_rels/workbook.xml.rels")
    root_rels = ET.fromstring(rels_xml)
    ns_rels = {"ns": "http://schemas.openxmlformats.org/package/2006/relationships"}
    
    target_path = None
    for rel in root_rels.findall(".//ns:Relationship", ns_rels):
        if rel.attrib.get("Id") == r_id:
            target_path = "xl/" + rel.attrib.get("Target")
            break
            
    if not target_path:
        return {}
        
    sheet_xml = z.read(target_path)
    root = ET.fromstring(sheet_xml)
    ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    
    rows = {}
    for row in root.findall(".//ns:row", ns):
        r_idx = int(row.attrib.get("r"))
        row_data = {}
        for c in row.findall("ns:c", ns):
            r_coord = c.attrib.get("r")
            col_letter = re.match(r"^([A-Z]+)", r_coord).group(1)
            t = c.attrib.get("t")
            v_elem = c.find("ns:v", ns)
            val = None
            if v_elem is not None:
                val = v_elem.text
                if t == "s" and val is not None:
                    idx = int(val)
                    if idx < len(shared_strings):
                        val = shared_strings[idx]
            row_data[col_letter] = val
        rows[r_idx] = row_data
    return rows

def load_answer_key(xlsx_path):
    if not Path(xlsx_path).exists():
        print(f"Warning: Answer key Excel file not found at {xlsx_path}")
        return {}
        
    with zipfile.ZipFile(xlsx_path, "r") as z:
        shared_strings = get_xlsx_shared_strings(z)
        sheets = get_xlsx_sheets(z)
        
        db = {}
        for name, sheet_id, r_id in sheets:
            rows = parse_sheet(z, r_id, shared_strings)
            if not rows:
                continue
                
            dup_map = {}
            row1 = rows.get(1, {})
            row2 = rows.get(2, {})
            for col, key in row1.items():
                if key and col in row2:
                    val = row2[col]
                    if val and re.match(r"^[A-Z]$", str(key)) and re.match(r"^[\d,]+$", str(val).strip()):
                        dup_map[str(key)] = [int(x) for x in str(val).split(",")]
            
            row3 = rows.get(3, {})
            q_cols_3 = {str(val): col for col, val in row3.items() if val}
            
            row4 = rows.get(4, {})
            q_cols_4 = {str(val): col for col, val in row4.items() if val}
            
            subjects = {}
            for r_idx in sorted(rows.keys()):
                if r_idx < 5:
                    continue
                row_data = rows[r_idx]
                grade = row_data.get("A")
                subject_name = row_data.get("B")
                if not subject_name:
                    continue
                
                subjects[subject_name] = {
                    "grade": grade,
                    "row": row_data,
                    "q_cols_3": q_cols_3,
                    "q_cols_4": q_cols_4,
                    "dup_map": dup_map,
                    "row_idx": r_idx
                }
            db[name] = subjects
        return db

def get_column_letter_from_index(col_idx):
    val = col_idx + 3  # 0 maps to 3 (Column C)
    letters = []
    while val > 0:
        val, remainder = divmod(val - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))

def get_correct_answers(db, year, subject, q_num, start_q):
    year_db = db.get(year)
    if not year_db:
        return [1], "정답표 Excel 파일에서 연도 시트를 찾을 수 없습니다."
    sub_db = year_db.get(subject)
    if not sub_db:
        return [1], f"정답표 Excel 파일 {year} 시트에서 '{subject}' 과목을 찾을 수 없습니다."
        
    col_idx = q_num - start_q
    if col_idx < 0:
        return [1], "정답표 매칭 오류: 문제 번호가 유효 범위를 벗어났습니다."
        
    col = get_column_letter_from_index(col_idx)
    raw_val = sub_db["row"].get(col)
    row_idx = sub_db.get("row_idx", "N/A")
    
    if raw_val is None:
        return [1], f"정답표.xlsx > {year} 시트 > {subject} ({row_idx}행) > {col}열: 등록된 값이 없습니다."
        
    dup_map = sub_db["dup_map"]
    raw_str = str(raw_val).strip()
    if raw_str in dup_map:
        ans_list = dup_map[raw_str]
        ans_str = ", ".join(map(str, ans_list))
        evidence = f"정답표.xlsx > {year} 시트 > {subject} ({row_idx}행) > {col}열의 값: '{raw_val}' (중복정답 대조표에 의해 {ans_str}번 복수 정답)"
        return ans_list, evidence
        
    try:
        ans_list = [int(raw_str)]
        evidence = f"정답표.xlsx > {year} 시트 > {subject} ({row_idx}행) > {col}열의 값: '{raw_val}' (정답: {raw_val}번)"
        return ans_list, evidence
    except ValueError:
        if "," in raw_str:
            ans_list = [int(x) for x in raw_str.split(",")]
            ans_str = ", ".join(map(str, ans_list))
            evidence = f"정답표.xlsx > {year} 시트 > {subject} ({row_idx}행) > {col}열의 값: '{raw_val}' (복수 정답: {ans_str}번)"
            return ans_list, evidence
        evidence = f"정답표.xlsx > {year} 시트 > {subject} ({row_idx}행) > {col}열의 값: '{raw_val}'"
        return [raw_str], evidence

# --- OCR parsing & Cropping ---
def parse_ocr_results(ocr_json_path):
    if not ocr_json_path.exists():
        return None
    data = json.loads(ocr_json_path.read_text(encoding="utf-8-sig"))
    return data

def generate_excel_evidence_image(answer_db, year, subject, q_num, start_q, out_dir):
    year_db = answer_db.get(year)
    if not year_db:
        return None
    sub_db = year_db.get(subject)
    if not sub_db:
        return None
        
    row_data = sub_db["row"]
    row_idx = sub_db.get("row_idx", 5)
    
    doc = fitz.open()
    # Width is 30 (left margin) + 40 (A) + 120 (B) + 35 * 40 (C..AK) + 30 (right margin) = 1620
    page = doc.new_page(width=1620, height=180)
    
    # Draw Title
    page.insert_text(fitz.Point(30, 25), f"정답표.xlsx 검증: {year}학년도 > {subject} ({row_idx}행) > Q{q_num} 근거 제시", fontsize=12, color=(0.1, 0.1, 0.3))
    
    start_x = 30
    start_y = 45
    row_height = 25
    col_width = 40
    
    columns = []
    for i in range(1, 38): # A to AK
        if i <= 26:
            columns.append(chr(64 + i))
        else:
            columns.append("A" + chr(64 + i - 26))
            
    row3_headers = {col: str(col_idx + 1) for col_idx, col in enumerate(columns[2:])}
    row4_headers = {col: str(col_idx + 36) for col_idx, col in enumerate(columns[2:])}
    
    display_rows = [
        {"label": "Row 3", "data": row3_headers, "type": "header1"},
        {"label": "Row 4", "data": row4_headers, "type": "header2"},
        {"label": f"Row {row_idx}", "data": row_data, "type": "subject"}
    ]
    
    target_col_idx = q_num - start_q
    target_col = get_column_letter_from_index(target_col_idx) if target_col_idx >= 0 else None
    
    for r_idx_in_loop, r_info in enumerate(display_rows):
        curr_y = start_y + r_idx_in_loop * row_height
        curr_data = r_info["data"]
        
        # Row label
        page.insert_text(fitz.Point(start_x - 25, curr_y + 17), r_info["label"], fontsize=8, color=(0.4, 0.4, 0.4))
        
        for c_idx, col_letter in enumerate(columns):
            if col_letter == "A":
                w = 40
            elif col_letter == "B":
                w = 120
            else:
                w = col_width
                
            curr_x = start_x
            for prev_c in columns[:c_idx]:
                if prev_c == "A": curr_x += 40
                elif prev_c == "B": curr_x += 120
                else: curr_x += col_width
                
            cell_rect = fitz.Rect(curr_x, curr_y, curr_x + w, curr_y + row_height)
            
            # BG Color
            bg_color = (0.96, 0.96, 0.96)
            if r_info["type"] == "subject":
                if col_letter == "A":
                    val_str = str(row_data.get("A") or "")
                elif col_letter == "B":
                    val_str = subject
                else:
                    val_str = str(curr_data.get(col_letter) or "")
                    if val_str and val_str != "None":
                        bg_color = (0.88, 0.95, 0.88)
            else:
                if col_letter == "A":
                    val_str = "학년" if r_info["type"] == "header1" else ""
                elif col_letter == "B":
                    val_str = "교과목명" if r_info["type"] == "header1" else ""
                else:
                    val_str = str(curr_data.get(col_letter) or "")
                bg_color = (0.9, 0.9, 0.94)
                
            is_target_column = (target_col and col_letter == target_col)
            
            # Draw Cell
            page.draw_rect(cell_rect, color=(0.75, 0.75, 0.75), fill=bg_color, width=1)
            
            # Draw Value
            if val_str and val_str != "None":
                txt_color = (0.1, 0.1, 0.1)
                if is_target_column and r_info["type"] == "subject":
                    txt_color = (0.8, 0.1, 0.1)
                page.insert_text(fitz.Point(curr_x + 4, curr_y + 17), val_str[:12], fontsize=9, color=txt_color)
                
            # Highlight target column cells
            if is_target_column:
                is_active_header = (r_info["type"] == "header1" and q_num <= 35) or (r_info["type"] == "header2" and q_num >= 36)
                if is_active_header or r_info["type"] == "subject":
                    page.draw_rect(cell_rect, color=(1.0, 0.0, 0.0), width=2.0)
                    
    if target_col:
        target_x = start_x
        for prev_c in columns:
            if prev_c == target_col:
                break
            if prev_c == "A": target_x += 40
            elif prev_c == "B": target_x += 120
            else: target_x += col_width
            
        arrow_x = target_x + col_width / 2
        arrow_y = start_y + 3 * row_height
        
        # Red arrow pointer line
        page.draw_line(fitz.Point(arrow_x, arrow_y), fitz.Point(arrow_x, arrow_y + 12), color=(1.0, 0.0, 0.0), width=1.5)
        
        dup_map = sub_db["dup_map"]
        target_val = str(row_data.get(target_col) or "").strip()
        if target_val in dup_map:
            ans_str = ", ".join(map(str, dup_map[target_val]))
            desc = f"Q{q_num} 정답: {target_val} ({ans_str}번 복수 정답)"
        else:
            desc = f"Q{q_num} 정답: {target_val}번 ({target_col}열)"
            
        page.insert_text(fitz.Point(arrow_x - 45, arrow_y + 25), desc, fontsize=9, color=(1.0, 0.0, 0.0))
        
    total_w = 40 + 120 + 35 * col_width
    crop_rect = fitz.Rect(10, 5, start_x + total_w + 10, start_y + 3 * row_height + 35)
    
    filename = f"excel_evidence_{year}_{subject}_q{q_num:02d}.png"
    out_path = out_dir / filename
    
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=crop_rect)
    pix.save(str(out_path))
    return filename

def determine_start_q(detected_qs, num_questions):
    if not detected_qs:
        return 36
    
    detected_set = set(detected_qs)
    best_starts = []
    best_score = -1
    
    for candidate in range(1, 101):
        expected_range = set(range(candidate, candidate + num_questions))
        score = len(detected_set.intersection(expected_range))
        if score > best_score:
            best_score = score
            best_starts = [candidate]
        elif score == best_score:
            best_starts.append(candidate)
            
    # Tie-breaking logic:
    # 1. Prefer candidates ending in 1 or 6 (e.g. 1, 26, 31, 36, 51, 56, 61, 71...)
    preferred = [c for c in best_starts if c % 10 in (1, 6)]
    if preferred:
        return preferred[0]
    
    # 2. Otherwise prefer the smallest candidate
    return best_starts[0]

def process_pdf(pdf_path, answer_db):
    print(f"\n================ Processing PDF: {pdf_path.name} ================")
    # Extract properties from filename: e.g. "2018_Java프로그래밍_3학년_2교시.pdf"
    # Format: [Year]_[Subject]_[Grade]_[Period].pdf
    name_parts = pdf_path.stem.split("_")
    if len(name_parts) < 2:
        print(f"Skipping PDF {pdf_path.name} because filename is not in [Year]_[Subject]_[Grade]_[Period] format.")
        return []
        
    year = name_parts[0]
    subject = name_parts[1]
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"Year: {year}, Subject: {subject}, Total pages: {total_pages}")
    
    # 1. Render all pages as high-resolution PNGs first (if not already rendered)
    SAMPLES_DIR.mkdir(exist_ok=True)
    page_images = []
    for page_idx in range(total_pages):
        filename = f"{year}_{subject}_page_{page_idx+1}.png"
        img_path = SAMPLES_DIR / filename
        page_images.append(img_path)
        if not img_path.exists():
            print(f"Rendering page {page_idx+1}/{total_pages}...")
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            pix.save(str(img_path))
            
    # 2. Run OCR via PowerShell on these images
    OCR_RESULTS_DIR.mkdir(exist_ok=True)
    print("Running OCR on page images...")
    subprocess.run([
        "powershell", "-ExecutionPolicy", "Bypass",
        "-File", str(ROOT / "ocr_pdf_pages.ps1"),
        "-ImageDir", str(SAMPLES_DIR),
        "-OutDir", str(OCR_RESULTS_DIR)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 3. Parse OCR JSONs to find question coordinates
    questions = []
    group_headers = [] # holds: { page, col, text, y, start_q, end_q }
    
    q_re = re.compile(r"^\s*(\d{1,2})(?:\.|\s|$)")
    group_re = re.compile(r"※\s*.*\((\d{1,2})\s*~\s*(\d{1,2})\)")
    
    page_q_positions = {} # page_idx -> { 'left': [ (q_num, y, text) ], 'right': [ (q_num, y, text) ] }
    
    for page_idx in range(total_pages):
        ocr_file = OCR_RESULTS_DIR / f"{year}_{subject}_page_{page_idx+1}_ocr.json"
        ocr_data = parse_ocr_results(ocr_file)
        if not ocr_data:
            print(f"Warning: OCR results not found for page {page_idx+1}")
            continue
            
        width = ocr_data["width"]
        height = ocr_data["height"]
        mid_x = width / 2
        
        left_qs = []
        right_qs = []
        
        for line in ocr_data["lines"]:
            text = line["text"]
            box = line["box"]
            x = box["x"]
            y = box["y"]
            w = box["w"]
            h = box["h"]
            
            # Skip header and footer zones
            if y < 100 or y > height - 100:
                continue
                
            is_left = (x + w/2) < mid_x
            
            # Detect group headers (e.g. ※ 다음... (51~53))
            g_match = group_re.search(text)
            if g_match:
                start_q = int(g_match.group(1))
                end_q = int(g_match.group(2))
                group_headers.append({
                    "page": page_idx + 1,
                    "col": "left" if is_left else "right",
                    "text": text,
                    "y": y,
                    "start_q": start_q,
                    "end_q": end_q
                })
                
            # Detect question numbers
            q_match = q_re.match(text)
            if q_match:
                q_num = int(q_match.group(1))
                is_valid_q = (is_left and x < 85) or ((not is_left) and x > 710 and x < 765)
                
                if is_valid_q:
                    if is_left:
                        left_qs.append((q_num, y, text))
                    else:
                        right_qs.append((q_num, y, text))
                        
        # Sort vertically
        left_qs.sort(key=lambda item: item[1])
        right_qs.sort(key=lambda item: item[1])
        
        page_q_positions[page_idx + 1] = {
            "left": left_qs,
            "right": right_qs,
            "height": height
        }
        
    # 4. Crop the questions and construct the questions database
    OUT_DIR.mkdir(exist_ok=True)
    
    # Pre-generate cropped group context images
    # A context image is from group_header_y to the first question in the group's Y-coord.
    context_files = {} # (page, start_q, end_q) -> filename
    for group in group_headers:
        p_idx = group["page"]
        col = group["col"]
        start_q = group["start_q"]
        end_q = group["end_q"]
        
        # Find the Y of the first question in this group on this page
        pos_info = page_q_positions.get(p_idx, {})
        qs_in_col = pos_info.get(col, [])
        first_q_y = None
        for q_num, y_coord, _ in qs_in_col:
            if q_num == start_q:
                first_q_y = y_coord
                break
                
        if first_q_y is None:
            first_q_y = pos_info.get("height", 2064) - 100
            
        # Coordinates in OCR (2.0 scale)
        x0 = 40 if col == "left" else 730
        x1 = 720 if col == "left" else 1410
        y0 = group["y"]
        y1 = first_q_y
        
        # Crop context
        context_filename = f"{year}_{subject}_context_{start_q}_{end_q}.png"
        context_path = OUT_DIR / context_filename
        
        page = doc[p_idx - 1]
        pdf_rect = fitz.Rect(x0 / 2.0, (y0 - 10) / 2.0, x1 / 2.0, (y1 - 10) / 2.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=pdf_rect)
        pix.save(str(context_path))
        
        context_files[(p_idx, start_q, end_q)] = context_filename
        print(f"Cropped context for Q{start_q}~Q{end_q} on page {p_idx} ({col} column)")
        
    # Calculate start_q by finding the S that matches Excel best
    all_detected_qs = []
    for p_idx, pos in page_q_positions.items():
        for col in ["left", "right"]:
            for q_num, y, text in pos[col]:
                all_detected_qs.append(q_num)
                
    num_questions = 25  # default
    year_db = answer_db.get(year)
    if year_db:
        sub_db = year_db.get(subject)
        if sub_db:
            col_idx = 0
            while True:
                col = get_column_letter_from_index(col_idx)
                val = sub_db["row"].get(col)
                if val is None or str(val).strip() == "":
                    break
                col_idx += 1
            if col_idx > 0:
                num_questions = col_idx
                
    start_q_pdf = determine_start_q(all_detected_qs, num_questions)
    print(f"Detected {len(all_detected_qs)} raw question indicators. Expected {num_questions} questions.")
    print(f"Calibrated starting question number to: {start_q_pdf}")
    
    valid_range = range(start_q_pdf, start_q_pdf + num_questions)
    
    # Filter page_q_positions to only contain valid question numbers
    filtered_page_q_positions = {}
    for p_idx, pos in page_q_positions.items():
        filtered_page_q_positions[p_idx] = {
            "height": pos["height"],
            "left": [item for item in pos["left"] if item[0] in valid_range],
            "right": [item for item in pos["right"] if item[0] in valid_range]
        }

    # Crop each question and save metadata
    for p_idx, pos in sorted(filtered_page_q_positions.items()):
        height = pos["height"]
        page = doc[p_idx - 1]
        
        for col in ["left", "right"]:
            qs = pos[col]
            x0 = 40 if col == "left" else 730
            x1 = 720 if col == "left" else 1410
            
            for idx, (q_num, y0, text) in enumerate(qs):
                # End Y is the start Y of the next question in the same column,
                # or bottom of the column if it's the last question
                if idx < len(qs) - 1:
                    y1 = qs[idx + 1][1]
                else:
                    y1 = height - 100 # Footer margin
                    
                # Crop question
                q_filename = f"{year}_{subject}_q{q_num:02d}.png"
                q_path = OUT_DIR / q_filename
                
                pdf_rect = fitz.Rect(x0 / 2.0, (y0 - 10) / 2.0, x1 / 2.0, (y1 - 10) / 2.0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=pdf_rect)
                pix.save(str(q_path))
                
                # Check if this question is part of any group context
                images_list = []
                for (gp_page, start_q, end_q), c_file in context_files.items():
                    if start_q <= q_num <= end_q:
                        images_list.append(c_file)
                        
                images_list.append(q_filename)
                
                # Read correct answers from answer_db with start_q calibration
                correct_ans, evidence_text = get_correct_answers(answer_db, year, subject, q_num, start_q_pdf)
                
                # Generate custom excel evidence screenshot
                excel_img = generate_excel_evidence_image(answer_db, year, subject, q_num, start_q_pdf, OUT_DIR)
                
                # Fetch pre-generated explanation, or fallback
                explanation = EXPLANATIONS.get(year, {}).get(q_num, "")
                if not explanation:
                    if correct_ans:
                        ans_str = ", ".join(map(str, correct_ans))
                        explanation = f"정답은 {ans_str}번입니다. 상세 해설이 아직 등록되지 않았습니다."
                    else:
                        explanation = "등록된 해설이 없습니다."
                        
                # Extract choices (보기) texts from the OCR results
                choices = []
                ocr_file = OCR_RESULTS_DIR / f"{year}_{subject}_page_{p_idx}_ocr.json"
                ocr_data = parse_ocr_results(ocr_file)
                if ocr_data:
                    q_lines = []
                    for line in ocr_data["lines"]:
                        l_box = line["box"]
                        l_x = l_box["x"]
                        l_y = l_box["y"]
                        l_w = l_box["w"]
                        
                        l_is_left = (l_x + l_w/2) < (ocr_data["width"] / 2)
                        col_matches = (col == "left" and l_is_left) or (col == "right" and not l_is_left)
                        
                        # Add a small buffer to Y bounds
                        if col_matches and (y0 + 15 < l_y < y1 - 5):
                            q_lines.append(line)
                            
                    # Group lines by Y-coordinate (tolerance of 15px)
                    q_lines.sort(key=lambda x: x["box"]["y"])
                    
                    rows = []
                    for line in q_lines:
                        l_y = line["box"]["y"]
                        added = False
                        for row in rows:
                            avg_y = sum(x["box"]["y"] for x in row) / len(row)
                            if abs(l_y - avg_y) < 15:
                                row.append(line)
                                added = True
                                break
                        if not added:
                            rows.append([line])
                            
                    # Sort each row horizontally by X
                    for row in rows:
                        row.sort(key=lambda x: x["box"]["x"])
                        
                    # Flatten the rows to get the sorted list of option blocks
                    blocks = []
                    for row in rows:
                        for line in row:
                            blocks.append(line["text"])
                            
                    # Clean up common OCR prefix errors: e.g. circled numbers, or artifacts like '', '@', 'O', ''
                    cleaned_blocks = []
                    for block in blocks:
                        cleaned = block.strip()
                        cleaned = re.sub(r"^[①②③④\s]+", "", cleaned)
                        cleaned = re.sub(r"^[^\w\s]\s*", "", cleaned)
                        cleaned = re.sub(r"^[Oo9K]\s*(?=[a-zA-Z])", "", cleaned)
                        cleaned_blocks.append(cleaned)
                        
                    if len(cleaned_blocks) == 4:
                        choices = cleaned_blocks
                        
                # If option parsing failed or was incomplete, default to generic numbers
                if len(choices) < 4:
                    choices = ["①번 보기", "②번 보기", "③번 보기", "④번 보기"]
                    
                questions.append({
                    "id": f"{year}_{subject}_q{q_num:02d}",
                    "year": int(year),
                    "subject": subject,
                    "q_num": q_num,
                    "page": p_idx,
                    "images": images_list,
                    "answer": correct_ans or [1], # Fallback to 1 if not found
                    "evidence": evidence_text,
                    "excel_image": excel_img,
                    "explanation": explanation,
                    "choices": choices
                })
                
    print(f"Processed {len(questions)} questions for {year} {subject}")
    return questions

def main():
    print("Loading answer keys from Excel...")
    answer_db = load_answer_key(str(EXCEL_PATH))
    
    all_questions = []
    
    # Scan 기출문제 folder for PDF files
    if not PDF_DIR.exists():
        print(f"Error: PDF source directory '{PDF_DIR}' does not exist.")
        return
        
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in 기출문제 folder.")
        return
        
    for pdf_file in pdf_files:
        try:
            questions = process_pdf(pdf_file, answer_db)
            all_questions.extend(questions)
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            import traceback
            traceback.print_exc()
            
    # Save database to questions.json
    OUT_JSON.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(all_questions)} questions to {OUT_JSON}")
    
    # Save static window.QUESTIONS database inside data.js for simple local deployment
    js_content = f"window.QUESTIONS = {json.dumps(all_questions, ensure_ascii=False, indent=2)};\n"
    OUT_DATA_JS.write_text(js_content, encoding="utf-8")
    print(f"Saved static database to {OUT_DATA_JS}")

if __name__ == "__main__":
    main()
