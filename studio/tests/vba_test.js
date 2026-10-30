// VBA 실행기(vba.js) 시험 - 모듈 소스를 컴파일해 셀 수식에서 부른 값이 엑셀과 같은지. 기대값은 엑셀(365)에서 같은 코드로 확인한 것.
const path = require("path");
const V = require(path.join(__dirname, "..", "vba.js"));
const C = require(path.join(__dirname, "..", "sheetcalc.js"));
const fails = [];
let ok = 0;
const check = (name, got, want) => { const g = JSON.stringify(got), w = JSON.stringify(want); if (g === w) ok++; else { fails.push(name); console.log(`FAIL ${name} → ${g} (기대 ${w})`); } };

const CODE = `Option Explicit
Const SEP As String = ","
' 정렬해서 잇기 - J 열(순번)이 숫자인 행만, 순번 순으로(교환 정렬)
Function SortedJoinWithout(rngValues As Range, rngSort As Range, rngOrder As Range, Optional delimiter As String = ",") As String
    Dim arrValues() As Variant, arrSort() As Variant
    Dim i As Long, j As Long, tempVal As Variant, tempSort As Variant
    Dim result As String
    arrValues = rngValues.Value
    arrSort = rngSort.Value
    For i = LBound(arrSort, 1) To UBound(arrSort, 1) - 1
        For j = i + 1 To UBound(arrSort, 1)
            If Not IsEmpty(arrSort(i, 1)) And Not IsEmpty(arrSort(j, 1)) Then
                If IsNumeric(arrSort(i, 1)) And IsNumeric(arrSort(j, 1)) Then
                    If arrSort(i, 1) > arrSort(j, 1) Then
                        tempSort = arrSort(i, 1): arrSort(i, 1) = arrSort(j, 1): arrSort(j, 1) = tempSort
                        tempVal = arrValues(i, 1)
                        arrValues(i, 1) = arrValues(j, 1)
                        arrValues(j, 1) = tempVal
                    End If
                End If
            End If
        Next j
    Next i
    For i = LBound(arrValues, 1) To UBound(arrValues, 1)
        If Not IsEmpty(arrSort(i, 1)) And IsNumeric(arrSort(i, 1)) And arrValues(i, 1) <> "" Then
            result = result & arrValues(i, 1) & delimiter
        End If
    Next i
    If Len(result) > 0 Then
        SortedJoinWithout = Left(result, Len(result) - Len(delimiter))
    Else
        SortedJoinWithout = ""
    End If
End Function

Function Twice(ByVal x As Double) As Double
    Twice = x * 2
End Function

Private Sub Bump(n As Long)
    n = n + 10
End Sub

Function UseByRef(x)
    Dim k As Long
    k = x
    Bump k
    UseByRef = k
End Function

Function Grade(score)
    Select Case score
        Case Is >= 90: Grade = "A"
        Case 80 To 89: Grade = "B"
        Case 70, 71, 72: Grade = "C-"
        Case Else
            Grade = "F"
    End Select
End Function

Function CountNonEmpty(r As Range) As Long
    Dim c As Variant, n As Long
    For Each c In r
        If Not IsEmpty(c.Value) Then n = n + 1
    Next
    CountNonEmpty = n
End Function

Function Words(s As String) As Long
    Dim parts As Variant
    parts = Split(Trim(s), " ")
    Words = UBound(parts) - LBound(parts) + 1
End Function

Function Fact(n As Long) As Double
    If n <= 1 Then Fact = 1 Else Fact = n * Fact(n - 1)
End Function

Function Collatz(ByVal n As Long) As Long
    Dim steps As Long
    Do While n <> 1
        If n Mod 2 = 0 Then
            n = n \\ 2
        ElseIf n > 0 Then
            n = 3 * n + 1
        End If
        steps = steps + 1
    Loop
    Collatz = steps
End Function

Function Rev(s)
    Dim i As Integer, out As String
    For i = Len(s) To 1 Step -1
        out = out & Mid(s, i, 1)
    Next i
    Rev = out
End Function

Function SafeDiv(a, b)
    On Error Resume Next
    SafeDiv = "오류"
    SafeDiv = a / b
End Function

Function WsfSum(r As Range)
    WsfSum = Application.WorksheetFunction.Sum(r) + WorksheetFunction.Max(r)
End Function

Function Grow()
    Dim a() As Long, i As Long
    ReDim a(1 To 2)
    a(1) = 5: a(2) = 6
    ReDim Preserve a(1 To 4)
    a(4) = 9
    For i = 1 To 4
        Grow = Grow & a(i) & ";"
    Next
End Function

Function ToNum(x) As Long
    ToNum = x
End Function

Function Pair(a, b)
    Pair = Array(a, b)
End Function

Function Bad()
    With Application
        .Volatile
    End With
End Function
`;

const vb = V.compile([{ name: "Module1", kind: "std", code: CODE }, { name: "Sheet1", kind: "doc", code: "Function NotFromCell()\n NotFromCell = 1\nEnd Function\n" }]);
check("컴파일 오류 - With 만(그 함수만 못 씀)", vb.errors.map((e) => /With/.test(e.msg)), [true]);
check("문서 모듈 함수는 셀에서 못 부른다", vb.has("NotFromCell"), false);
C.setVba(vb, V);

const cells = {
  G1: "PROJECT_CD", G2: "IF_VRSN_ID", G3: "ITEM_CD", G4: "ITEM_NM", G5: "DESCR",
  J1: 2, J2: 3, J3: 1, J5: "x",
  A1: 1, A2: 2, A3: 3, A5: 10,
};
const F = {
  B1: "=SortedJoinWithout(G1:G5,J1:J5,K1:K5,\",\")", B2: "=SortedJoinWithout(G1:G5,J1:J5,K1:K5)", B3: "=sortedjoinwithout(G4:G5,J4:J5,K4:K5,\"-\")",
  B4: "=Twice(A2)+1", B5: "=UseByRef(5)", B6: "=Grade(95)&Grade(85)&Grade(71)&Grade(10)", B7: "=CountNonEmpty(A1:A5)", B8: "=Words(\"  a bb  ccc \")",
  B9: "=Fact(10)", B10: "=Collatz(27)", B11: "=Rev(\"가나다\")", B12: "=SafeDiv(1,0)", B13: "=SafeDiv(6,3)", B14: "=WsfSum(A1:A5)", B15: "=Grow()",
  B16: "=ToNum(2.5)&\",\"&ToNum(3.5)", B17: "=Bad()", B18: "=NotFromCell()", B19: "=SUM(Pair(3,4))", B20: "=Twice(\"글\")",
};
const doc = { sheets: [{ id: "t01", name: "S", cells: { ...cells } }] };
for (const [k, f] of Object.entries(F)) doc.sheets[0].cells[k] = { f };
C.recalc(doc);
const v = (k) => doc.sheets[0].cells[k].v;
check("SortedJoinWithout - 순번 순, 숫자 아닌 순번·빈 순번 행은 뺀다", v("B1"), "ITEM_CD,PROJECT_CD,IF_VRSN_ID");
check("선택 인수 기본값(delimiter = \",\")", v("B2"), "ITEM_CD,PROJECT_CD,IF_VRSN_ID");
check("이름 대소문자 무시 · 남는 게 없으면 빈 글", v("B3"), "");
check("ByVal Double · 셀 수식 안에서 섞어 쓰기", v("B4"), 5);
check("ByRef - Sub 가 부른 쪽 변수를 바꾼다", v("B5"), 15);
check("Select Case - Is · To · 목록 · Else", v("B6"), "ABC-F");
check("For Each 칸 · IsEmpty", v("B7"), 4);
check("Split · Trim · UBound", v("B8"), 4);
check("재귀 · 한 줄 If … Else", v("B9"), 3628800);
check("Do While · Mod · \\ · ElseIf", v("B10"), 111);
check("Step -1 · Mid", v("B11"), "다나가");
check("On Error Resume Next - 0 으로 나누면 앞의 값", v("B12"), "오류");
check("On Error 없이 정상", v("B13"), 2);
check("WorksheetFunction.Sum·Max (Application. 생략 가능)", v("B14"), 26);
check("ReDim Preserve · 콜론 여러 문장", v("B15"), "5;6;0;9;");
check("Long 대입은 짝수 반올림(2.5 → 2, 3.5 → 4)", v("B16"), "2,4");
check("못 쓰는 문법(With) 함수 - #NAME?(엑셀 저장값을 덮지 않는다)", v("B17"), "#NAME?");
check("문서 모듈 함수 - #NAME?", v("B18"), "#NAME?");
check("배열을 돌려주면 시트 배열(SUM)", v("B19"), 7);
check("형식 불일치 - #VALUE!", v("B20"), "#VALUE!");

const keep = { sheets: [{ id: "t01", name: "S", cells: { A1: { f: "=Bad()", v: "엑셀 값" } } }] };
C.recalc(keep);
check("못 쓰는 함수 칸은 엑셀이 저장한 값을 그대로", keep.sheets[0].cells.A1.v, "엑셀 값");

const loop = V.compile([{ name: "M", kind: "std", code: "Function Forever()\n Do\n Loop\nEnd Function\n" }]);
C.setVba(loop, V);
const d2 = { sheets: [{ id: "t01", name: "S", cells: { A1: { f: "=Forever()" } } }] };
const t0 = Date.now(); C.recalc(d2);
check("끝나지 않는 반복 - 한도에서 #VALUE!", [d2.sheets[0].cells.A1.v, Date.now() - t0 < 5000], ["#VALUE!", true]);
C.setVba(null);
const fn = (nm) => `Function ${nm}()\n ${nm} = 1\nEnd Function\n`;
check("모듈과 이름이 같은 함수는 칸에서 못 부른다(엑셀 #NAME?)", [V.compile([{ name: "Dup", kind: "std", code: fn("Dup") }]).has("Dup"), V.compile([{ name: "M2", kind: "std", code: fn("Dup2") }]).has("Dup2")], [false, true]);

// ---------------------------------------------------------------- 보안 한도(0.25.8) - 문서의 코드가 화면을 멈추거나 탭을 죽이지 못한다
const run1 = (code) => { const c = V.compile([{ name: "M", kind: "std", code }]); const t = Date.now(); try { return [c.call("F", []), Date.now() - t]; } catch (e) { return [e.constructor.name + ":" + e.message, Date.now() - t]; } };
const sec = {
  "배열 칸 한도": ["Function F()\n Dim a(1 To 300000000)\n F = 1\nEnd Function", /^VErr:배열이 너무 큽니다/],
  "ReDim 칸 한도": ["Function F()\n Dim a()\n ReDim a(1 To 20000, 1 To 20000)\n F = 1\nEnd Function", /^VErr:배열이 너무 큽니다/],
  "문자열 길이 한도(Space)": ["Function F()\n F = Len(Space(2000000000))\nEnd Function", /^VErr:문자열이 너무 깁니다/],
  "문자열 길이 한도(& 두 배씩)": ["Function F()\n s = \"x\"\n For i = 1 To 40\n s = s & s\n Next\n F = Len(s)\nEnd Function", /^VErr:문자열이 너무 깁니다/],
  "부르기 깊이 한도": ["Function F(Optional n = 0)\n F = F(n + 1)\nEnd Function", /^VErr:스택 공간이 부족합니다/],
  "형식 이름 constructor 는 내부 개체가 아니다": ["Function F()\n Dim x As constructor\n F = TypeName(x)\nEnd Function", /^Empty$/],
  "잘못된 Like 패턴 - VBA 오류 93": ["Function F()\n F = \"a\" Like \"[z-a]\"\nEnd Function", /^VErr:패턴 문자열이 잘못되었습니다/],
};
for (const [nm, [code, re]] of Object.entries(sec)) { const [v2, ms] = run1(code); check(`보안 - ${nm}`, [re.test(String(v2)), ms < 3000], [true, true]); }
const [lk, lms] = run1("Function F()\n F = String(5000, \"a\") Like \"*a*a*a*a*a*a*a*a*a*a*a*a*b\"\nEnd Function");
check("보안 - Like 되짚기 폭주 없음(5000자·별 13개)", [lk, lms < 1000], [false, true]);
const L = (s, p) => run1(`Function F()\n F = "${s}" Like "${p}"\nEnd Function`)[0];
check("Like - * ? # [a-c] [!0-9] 엑셀과 같게", [L("abc", "a*"), L("abc", "a?c"), L("a1c", "a#c"), L("abc", "[a-c]bc"), L("xbc", "[!0-9]bc"), L("1bc", "[!0-9]bc"), L("a*c", "a[*]c"), L("", "*"), L("ab", "a*b*"), L("aXbXc", "a*b*c"), L("abc", "ABC")],
  [true, true, true, true, true, false, true, true, true, true, false]);
const dead = V.compile([{ name: "M", kind: "std", code: "Const K = 1\nFunction F()\n F = K\nEnd Function\nFunction G(\n" }]);
check("깨진 모듈도 컴파일은 오류 목록으로(화면이 죽지 않는다)", [Array.isArray(dead.errors), dead.call("F", [])], [true, 1]);
const deep = V.compile([{ name: "M", kind: "std", code: "Function F()\n" + "If 1 Then\n".repeat(20000) + "End If\n".repeat(20000) + "End Function\n" }]);
check("아주 깊은 중첩 - 그 모듈만 못 씀(스택 넘침을 오류 목록으로)", deep.errors.length > 0, true);

// Worker 주고받기 - 값 묶기·한 메시지 처리(vbaworker.js 가 쓰는 serve)
const R0 = new V.VRange([[1, { code: "#N/A" }], [null, "x"]], 2, 3, "S"), A0 = new V.VArr([[1, 2]], [V.EMPTY, new V.CVErr("#DIV/0!")]);
const back = JSON.parse(JSON.stringify([R0, A0, V.MISSING, 3, "s"].map(V.pack))).map(V.unpack);
check("pack·unpack - Range·배열·Missing·값", [back[0] instanceof V.VRange && back[0].r0 === 2 && back[0].rows[0][1].code, back[1] instanceof V.VArr && back[1].d[0] === V.EMPTY && back[1].d[1].code, back[2] === V.MISSING, back[3], back[4]], ["#N/A", "#DIV/0!", true, 3, "s"]);
const st = {}; V.serve(st, { type: "init", modules: [{ name: "M", kind: "std", code: "Function Tw(x)\n Tw = x * 2\nEnd Function\nFunction W()\n With x\n End With\nEnd Function\nFunction Z(r)\n Z = r.Count\nEnd Function\n" }] }, {});
check("serve - 결과·못 쓰는 문법·실행 오류·Range 인자", [V.serve(st, { type: "call", id: 1, name: "Tw", args: [21] }, {}), V.serve(st, { type: "call", id: 2, name: "W", args: [] }, {}).err.kind, V.serve(st, { type: "call", id: 3, name: "Tw", args: ["글"] }, {}).err.kind, V.serve(st, { type: "call", id: 4, name: "Z", args: [V.pack(R0)] }, {}).v],
  [{ id: 1, v: 42 }, "unsupported", "verr", 4]);

// 계산 중(Pending) - 그 칸과 그 칸에 기대는 칸(IFERROR 로 감싸도)은 저장값을 그대로, 다른 칸은 계산
let pend = true;
const fake = { has: (n) => /^slow$/i.test(n), call: () => { if (pend) throw new V.Pending("계산 중"); return 7; } };
C.setVba(fake, V);
const dp = { sheets: [{ id: "t01", name: "S", cells: { A1: { f: "=Slow()", v: 5 }, A2: { f: "=A1+1", v: 6 }, A3: { f: "=IFERROR(A1,0)", v: 5 }, A4: { f: "=1+1" }, B1: { f: "=SEQUENCE(2)+Slow()", v: 6, da: 1 }, B2: { v: 7, sp: "B1" } } }] };
C.recalc(dp);
const cv = (k) => dp.sheets[0].cells[k].v;
check("Pending - 기다리는 칸·기대는 칸·넘친 칸은 저장값 그대로, 나머지는 계산", [cv("A1"), cv("A2"), cv("A3"), cv("A4"), cv("B1"), cv("B2"), dp.sheets[0].cells.B2.sp], [5, 6, 5, 2, 6, 7, "B1"]);
pend = false; C.recalc(dp);
check("결과가 오면 다시 계산", [cv("A1"), cv("A2"), cv("A3"), cv("B1"), cv("B2")], [7, 8, 7, 8, 9]);
C.setVba(null);

console.log(`VBA 사례 ${ok + fails.length}개 중 ${ok}개 같음`);
console.log("\n실패:", fails.length ? fails.join(", ") : "없음");
process.exit(fails.length ? 1 : 0);
