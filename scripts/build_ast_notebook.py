"""Generate ast_to_neo4j.ipynb. Run once: python scripts/build_ast_notebook.py"""
import json
from pathlib import Path

NB_PATH = Path(__file__).resolve().parent.parent / "ast_to_neo4j.ipynb"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _src(lines)}


def code(*lines):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _src(lines),
    }


def _src(lines):
    text = "\n".join(lines)
    parts = text.split("\n")
    out = []
    for i, p in enumerate(parts):
        if i < len(parts) - 1:
            out.append(p + "\n")
        else:
            if p:
                out.append(p)
    return out


JAVA_EXTRACTOR = r'''
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.ImportDeclaration;
import com.github.javaparser.ast.NodeList;
import com.github.javaparser.ast.body.*;
import com.github.javaparser.ast.expr.*;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

public class AstExtractor {

    public static void main(String[] args) throws Exception {
        String filePath = args[0];
        String outPath = args[1];

        CompilationUnit cu = StaticJavaParser.parse(new File(filePath));

        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"file\":").append(s(filePath)).append(",");
        sb.append("\"package\":").append(s(
                cu.getPackageDeclaration().map(p -> p.getNameAsString()).orElse(""))).append(",");

        List<String> imps = new ArrayList<>();
        for (ImportDeclaration imp : cu.getImports()) imps.add(s(imp.getNameAsString()));
        sb.append("\"imports\":[").append(String.join(",", imps)).append("],");

        List<String> classJsons = new ArrayList<>();
        for (ClassOrInterfaceDeclaration cls : cu.findAll(ClassOrInterfaceDeclaration.class)) {
            StringBuilder cb = new StringBuilder();
            cb.append("{");
            cb.append("\"name\":").append(s(cls.getNameAsString())).append(",");
            cb.append("\"isInterface\":").append(cls.isInterface()).append(",");

            List<String> anns = new ArrayList<>();
            for (AnnotationExpr a : cls.getAnnotations()) anns.add(annJson(a));
            cb.append("\"annotations\":[").append(String.join(",", anns)).append("],");

            List<String> fields = new ArrayList<>();
            for (FieldDeclaration f : cls.getFields()) {
                for (VariableDeclarator v : f.getVariables()) {
                    fields.add("{\"name\":" + s(v.getNameAsString())
                            + ",\"type\":" + s(v.getTypeAsString()) + "}");
                }
            }
            cb.append("\"fields\":[").append(String.join(",", fields)).append("],");

            List<String> methods = new ArrayList<>();
            for (MethodDeclaration m : cls.getMethods()) {
                methods.add(methodJson(m.getNameAsString(), m.getTypeAsString(),
                        paramTypes(m.getParameters()), m.getAnnotations(), findCalls(m),
                        m.getBegin().map(p -> p.line).orElse(-1)));
            }
            for (ConstructorDeclaration c : cls.getConstructors()) {
                methods.add(methodJson("<init>", cls.getNameAsString(),
                        paramTypes(c.getParameters()), c.getAnnotations(), findCalls(c),
                        c.getBegin().map(p -> p.line).orElse(-1)));
            }
            cb.append("\"methods\":[").append(String.join(",", methods)).append("]");

            cb.append("}");
            classJsons.add(cb.toString());
        }
        sb.append("\"classes\":[").append(String.join(",", classJsons)).append("]");
        sb.append("}");

        Files.write(Paths.get(outPath), sb.toString().getBytes("UTF-8"));
        System.out.println("OK -> " + outPath);
    }

    static List<String> paramTypes(NodeList<Parameter> ps) {
        List<String> r = new ArrayList<>();
        for (Parameter p : ps) r.add(p.getTypeAsString());
        return r;
    }

    static String methodJson(String name, String returnType, List<String> paramTypes,
                             NodeList<AnnotationExpr> annotations, List<String[]> calls,
                             int line) {
        StringBuilder b = new StringBuilder();
        b.append("{\"name\":").append(s(name)).append(",");
        b.append("\"returnType\":").append(s(returnType)).append(",");
        b.append("\"line\":").append(line).append(",");
        List<String> ps = new ArrayList<>();
        for (String t : paramTypes) ps.add(s(t));
        b.append("\"params\":[").append(String.join(",", ps)).append("],");
        List<String> anns = new ArrayList<>();
        for (AnnotationExpr a : annotations) anns.add(annJson(a));
        b.append("\"annotations\":[").append(String.join(",", anns)).append("],");
        List<String> cs = new ArrayList<>();
        for (String[] c : calls) {
            cs.add("{\"scope\":" + s(c[0]) + ",\"name\":" + s(c[1]) + ",\"argc\":" + c[2] + "}");
        }
        b.append("\"calls\":[").append(String.join(",", cs)).append("]");
        b.append("}");
        return b.toString();
    }

    static List<String[]> findCalls(BodyDeclaration<?> body) {
        List<String[]> calls = new ArrayList<>();
        for (MethodCallExpr mc : body.findAll(MethodCallExpr.class)) {
            String scope = mc.getScope().map(Object::toString).orElse("");
            String name = mc.getNameAsString();
            int argc = mc.getArguments().size();
            calls.add(new String[]{scope, name, String.valueOf(argc)});
        }
        return calls;
    }

    static String annJson(AnnotationExpr a) {
        String name = a.getNameAsString();
        String value = "";
        if (a instanceof SingleMemberAnnotationExpr) {
            value = ((SingleMemberAnnotationExpr) a).getMemberValue().toString();
        } else if (a instanceof NormalAnnotationExpr) {
            value = a.toString();
        }
        return "{\"name\":" + s(name) + ",\"value\":" + s(value) + "}";
    }

    static String s(String v) {
        if (v == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < v.length(); i++) {
            char c = v.charAt(i);
            switch (c) {
                case '"':  b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        b.append("\"");
        return b.toString();
    }
}
'''.lstrip("\n")


cells = []

cells.append(md(
    "# Java AST → Neo4j Knowledge Graph",
    "",
    "`AuctionlandController.java` 를 **JavaParser** 로 파싱해 클래스/필드/메서드/메서드호출/임포트/어노테이션을 추출하고 **Neo4j** 에 지식 그래프로 적재합니다.",
    "",
    "- **범위**: `AuctionlandController.java` 1개 파일",
    "- **도구**: JavaParser (`javaparser-core` jar)",
    "- **메서드 호출 해석**: 빠름 (이름 매칭, symbol solver 미사용 → 외부 호출은 `:CallTarget` 노드로 표현)",
    "- **Neo4j**: `neo4j_env.txt` 에서 자격증명 로드",
    "",
    "## 셀 구성",
    "1. Python 의존성 설치",
    "2. Portable JDK 다운로드 (시스템 PATH 영향 0, `build/jdk/` 에 압축 해제)",
    "3. JDK 탐지 (portable → PATH → 일반 설치 경로 → IntelliJ jbr → VSCode 번들)",
    "4. 작업 경로 + JavaParser jar 다운로드",
    "5. Java 추출기 소스 적재 / 파일로 출력",
    "6. 컴파일",
    "7. 실행 → JSON",
    "8. 미리보기 (DataFrame)",
    "9. Neo4j 자격증명 로드",
    "10. 연결 + 제약조건",
    "11. 그래프 적재",
    "12. 검증 쿼리",
    "13. Neo4j Browser 시각화 쿼리",
))

cells.append(code(
    "# 1. Python 의존성",
    "%pip install -q neo4j pandas",
))

cells.append(code(
    "# 2. Portable JDK 다운로드 (시스템 무영향)",
    "#   - Adoptium API 로 최신 LTS(Temurin 17) Windows x64 zip 을 받아 build/jdk/ 에 풀고",
    "#     그 안의 javac.exe / java.exe 를 사용합니다.",
    "#   - 이미 풀려 있으면 스킵.",
    "import os, json, urllib.request, zipfile, shutil",
    "from pathlib import Path",
    "",
    "PROJECT_ROOT = Path(r'c:\\AI_Master_Project\\auctionland-backend')",
    "JDK_DIR      = PROJECT_ROOT / 'build' / 'jdk'",
    "JDK_DIR.mkdir(parents=True, exist_ok=True)",
    "",
    "def _portable_javac():",
    "    hits = list(JDK_DIR.glob('*/bin/javac.exe'))",
    "    return hits[0] if hits else None",
    "",
    "PORTABLE_JAVAC = _portable_javac()",
    "UA = {'User-Agent': 'Mozilla/5.0 (auctionland-ast-notebook)'}",
    "",
    "def _http_get(url, timeout=60):",
    "    req = urllib.request.Request(url, headers=UA)",
    "    return urllib.request.urlopen(req, timeout=timeout)",
    "",
    "def _http_download(url, dest):",
    "    req = urllib.request.Request(url, headers=UA)",
    "    with urllib.request.urlopen(req, timeout=300) as r, open(dest, 'wb') as f:",
    "        shutil.copyfileobj(r, f)",
    "",
    "if PORTABLE_JAVAC is None:",
    "    api = ('https://api.adoptium.net/v3/assets/feature_releases/17/ga'",
    "           '?architecture=x64&heap_size=normal&image_type=jdk&os=windows'",
    "           '&project=jdk&vendor=eclipse&page=0&page_size=1')",
    "    print('querying Adoptium ...')",
    "    with _http_get(api) as r:",
    "        data = json.loads(r.read().decode('utf-8'))",
    "    pkg = next(b['package'] for b in data[0]['binaries'] if b['package']['link'].endswith('.zip'))",
    "    zip_path = JDK_DIR / pkg['name']",
    "    print(f\"downloading {pkg['link']}\")",
    "    print(f\"  size: {pkg['size']:,} bytes\")",
    "    if not zip_path.exists():",
    "        _http_download(pkg['link'], zip_path)",
    "    print(f'extracting {zip_path.name} ...')",
    "    with zipfile.ZipFile(zip_path) as zf:",
    "        zf.extractall(JDK_DIR)",
    "    zip_path.unlink()",
    "    PORTABLE_JAVAC = _portable_javac()",
    "    if PORTABLE_JAVAC is None:",
    "        raise RuntimeError('JDK 압축 해제 후에도 javac.exe 를 찾지 못했습니다.')",
    "",
    "PORTABLE_JAVA = PORTABLE_JAVAC.with_name('java.exe')",
    "print(f'portable javac: {PORTABLE_JAVAC}')",
    "print(f'portable java : {PORTABLE_JAVA}')",
))

cells.append(code(
    "# 3. JDK 탐지 — portable 우선, 그 다음 PATH / 일반 설치 경로",
    "import shutil, glob",
    "",
    "def _find_javac():",
    "    if PORTABLE_JAVAC and PORTABLE_JAVAC.exists():",
    "        return PORTABLE_JAVAC",
    "    p = shutil.which('javac')",
    "    if p:",
    "        return Path(p)",
    "    home = os.environ.get('JAVA_HOME')",
    "    if home:",
    "        cand = Path(home) / 'bin' / 'javac.exe'",
    "        if cand.exists():",
    "            return cand",
    "    patterns = [",
    "        r'C:\\Program Files\\Java\\*\\bin\\javac.exe',",
    "        r'C:\\Program Files\\Eclipse Adoptium\\*\\bin\\javac.exe',",
    "        r'C:\\Program Files\\Microsoft\\*\\bin\\javac.exe',",
    "        r'C:\\Program Files\\Zulu\\*\\bin\\javac.exe',",
    "        r'C:\\Program Files\\Amazon Corretto\\*\\bin\\javac.exe',",
    "        r'C:\\Program Files\\JetBrains\\*\\jbr\\bin\\javac.exe',",
    "        os.path.expanduser(r'~\\.jdks\\*\\bin\\javac.exe'),",
    "        os.path.expanduser(r'~\\.vscode\\extensions\\redhat.java-*\\jre\\*\\bin\\javac.exe'),",
    "    ]",
    "    for pat in patterns:",
    "        hits = glob.glob(pat)",
    "        if hits:",
    "            return Path(sorted(hits)[-1])",
    "    return None",
    "",
    "JAVAC = _find_javac()",
    "if JAVAC is None:",
    "    raise RuntimeError('javac 를 찾지 못했습니다 — 셀 2를 다시 실행하세요.')",
    "JAVA = JAVAC.with_name('java.exe')",
    "print(f'javac: {JAVAC}')",
    "print(f'java : {JAVA}')",
    "import subprocess",
    "subprocess.run([str(JAVA), '-version'], check=True)",
))

cells.append(code(
    "# 4. 경로 설정 + JavaParser jar 다운로드",
    "TARGET_JAVA  = PROJECT_ROOT / 'src/main/java/com/example/demo/controller/AuctionlandController.java'",
    "WORK_DIR     = PROJECT_ROOT / 'build' / 'ast_extractor'",
    "WORK_DIR.mkdir(parents=True, exist_ok=True)",
    "",
    "JAVAPARSER_VERSION = '3.25.10'",
    "JAVAPARSER_JAR = WORK_DIR / f'javaparser-core-{JAVAPARSER_VERSION}.jar'",
    "JAVAPARSER_URL = (",
    "    'https://repo1.maven.org/maven2/com/github/javaparser/javaparser-core/'",
    "    f'{JAVAPARSER_VERSION}/javaparser-core-{JAVAPARSER_VERSION}.jar'",
    ")",
    "",
    "if not JAVAPARSER_JAR.exists():",
    "    print(f'Downloading {JAVAPARSER_URL} ...')",
    "    urllib.request.urlretrieve(JAVAPARSER_URL, JAVAPARSER_JAR)",
    "",
    "assert TARGET_JAVA.exists(), f'대상 파일이 없습니다: {TARGET_JAVA}'",
    "print(f'jar    : {JAVAPARSER_JAR}  ({JAVAPARSER_JAR.stat().st_size:,} bytes)')",
    "print(f'target : {TARGET_JAVA}')",
    "print(f'work   : {WORK_DIR}')",
))

cells.append(code(
    "# 5. Java 추출기 소스 작성",
    "EXTRACTOR_SRC = WORK_DIR / 'AstExtractor.java'",
    "EXTRACTOR_SRC.write_text(JAVA_SOURCE, encoding='utf-8')",
    "print(f'wrote: {EXTRACTOR_SRC}  ({len(JAVA_SOURCE):,} bytes)')",
))

# Insert the JAVA_SOURCE assignment as a separate cell preceding cell 4
java_src_cell = code(
    "# (5-pre) JavaParser 추출기 소스 (변수에 적재)",
    "JAVA_SOURCE = r\"\"\"" + JAVA_EXTRACTOR.replace('"""', '\\"\\"\\"') + "\"\"\"",
    "print(f'source size: {len(JAVA_SOURCE):,} chars')",
)
cells.insert(-1, java_src_cell)

cells.append(code(
    "# 6. 컴파일",
    "import subprocess",
    "result = subprocess.run(",
    "    [str(JAVAC), '-encoding', 'UTF-8', '-cp', str(JAVAPARSER_JAR), '-d', str(WORK_DIR), str(EXTRACTOR_SRC)],",
    "    capture_output=True, text=True,",
    ")",
    "print('STDOUT:', result.stdout)",
    "print('STDERR:', result.stderr)",
    "result.check_returncode()",
    "print('compiled:', WORK_DIR / 'AstExtractor.class')",
))

cells.append(code(
    "# 7. 실행 → JSON",
    "import json",
    "OUT_JSON = WORK_DIR / 'ast.json'",
    "SEP = ';' if os.name == 'nt' else ':'",
    "cp = SEP.join([str(JAVAPARSER_JAR), str(WORK_DIR)])",
    "result = subprocess.run(",
    "    [str(JAVA), '-cp', cp, 'AstExtractor', str(TARGET_JAVA), str(OUT_JSON)],",
    "    capture_output=True, text=True,",
    ")",
    "print('STDOUT:', result.stdout)",
    "print('STDERR:', result.stderr)",
    "result.check_returncode()",
    "",
    "with open(OUT_JSON, 'r', encoding='utf-8') as f:",
    "    ast = json.load(f)",
    "print(json.dumps(ast, indent=2, ensure_ascii=False)[:1500])",
))

cells.append(code(
    "# 8. 미리보기 (DataFrame)",
    "import pandas as pd",
    "from IPython.display import display",
    "",
    "print(f\"package: {ast['package']}\")",
    "print(f\"file   : {ast['file']}\")",
    "",
    "print('\\n# Imports')",
    "display(pd.DataFrame({'import': ast['imports']}))",
    "",
    "for cls in ast['classes']:",
    "    print(f\"\\n# Class: {cls['name']}  (interface={cls['isInterface']})\")",
    "    print('  Annotations:', [a['name'] for a in cls['annotations']])",
    "    print('  Fields:')",
    "    display(pd.DataFrame(cls['fields']) if cls['fields'] else pd.DataFrame(columns=['name','type']))",
    "    print('  Methods:')",
    "    rows = []",
    "    for m in cls['methods']:",
    "        rows.append({",
    "            'method': m['name'],",
    "            'line': m['line'],",
    "            'returnType': m['returnType'],",
    "            'params': ', '.join(m['params']),",
    "            'annotations': ', '.join(a['name'] for a in m['annotations']),",
    "            'calls': len(m['calls']),",
    "        })",
    "    display(pd.DataFrame(rows))",
    "    print('  CallSites:')",
    "    call_rows = []",
    "    for m in cls['methods']:",
    "        for c in m['calls']:",
    "            call_rows.append({'caller': m['name'], 'scope': c['scope'], 'callee': c['name'], 'argc': c['argc']})",
    "    display(pd.DataFrame(call_rows) if call_rows else pd.DataFrame(columns=['caller','scope','callee','argc']))",
))

cells.append(code(
    "# 9. Neo4j 자격증명 로드",
    "NEO4J_ENV = PROJECT_ROOT / 'neo4j_env.txt'",
    "neo4j_cfg = {}",
    "for line in NEO4J_ENV.read_text(encoding='utf-8').splitlines():",
    "    line = line.strip()",
    "    if not line or line.startswith('#'):",
    "        continue",
    "    if '=' in line:",
    "        k, v = line.split('=', 1)",
    "        neo4j_cfg[k.strip()] = v.strip()",
    "",
    "print({k: ('***' if 'PASSWORD' in k else v) for k, v in neo4j_cfg.items()})",
))

cells.append(code(
    "# 10. Neo4j 연결 + 제약조건",
    "from neo4j import GraphDatabase",
    "",
    "driver = GraphDatabase.driver(",
    "    neo4j_cfg['NEO4J_URI'],",
    "    auth=(neo4j_cfg['NEO4J_USERNAME'], neo4j_cfg['NEO4J_PASSWORD']),",
    ")",
    "DB_NAME = neo4j_cfg.get('NEO4J_DATABASE', 'neo4j')",
    "",
    "CONSTRAINTS = [",
    "    'CREATE CONSTRAINT file_path  IF NOT EXISTS FOR (f:File)        REQUIRE f.path IS UNIQUE',",
    "    'CREATE CONSTRAINT class_fqn  IF NOT EXISTS FOR (c:Class)       REQUIRE c.fqn  IS UNIQUE',",
    "    'CREATE CONSTRAINT method_id  IF NOT EXISTS FOR (m:Method)      REQUIRE m.id   IS UNIQUE',",
    "    'CREATE CONSTRAINT field_id   IF NOT EXISTS FOR (fd:Field)      REQUIRE fd.id  IS UNIQUE',",
    "    'CREATE CONSTRAINT ann_name   IF NOT EXISTS FOR (a:Annotation)  REQUIRE a.name IS UNIQUE',",
    "    'CREATE CONSTRAINT import_fqn IF NOT EXISTS FOR (i:Import)      REQUIRE i.fqn  IS UNIQUE',",
    "    'CREATE CONSTRAINT calltarget_id IF NOT EXISTS FOR (t:CallTarget) REQUIRE t.id IS UNIQUE',",
    "]",
    "with driver.session(database=DB_NAME) as s:",
    "    for q in CONSTRAINTS:",
    "        s.run(q)",
    "    rec = s.run('RETURN \"connected to \" + $db AS msg', db=DB_NAME).single()",
    "    print(rec['msg'])",
))

cells.append(code(
    "# 11. 그래프 적재 (MERGE 기반 idempotent)",
    "def upsert_graph(tx, ast):",
    "    file_path = ast['file']",
    "    pkg = ast['package']",
    "    tx.run('MERGE (f:File {path:$path}) SET f.package=$pkg', path=file_path, pkg=pkg)",
    "",
    "    for imp in ast['imports']:",
    "        tx.run('''",
    "            MATCH (f:File {path:$path})",
    "            MERGE (i:Import {fqn:$fqn})",
    "            MERGE (f)-[:IMPORTS]->(i)",
    "        ''', fqn=imp, path=file_path)",
    "",
    "    for cls in ast['classes']:",
    "        fqn = (pkg + '.' if pkg else '') + cls['name']",
    "        tx.run('''",
    "            MATCH (f:File {path:$path})",
    "            MERGE (c:Class {fqn:$fqn})",
    "            SET c.name=$name, c.isInterface=$isInterface",
    "            MERGE (f)-[:DECLARES]->(c)",
    "        ''', fqn=fqn, name=cls['name'], isInterface=cls['isInterface'], path=file_path)",
    "",
    "        for a in cls['annotations']:",
    "            tx.run('''",
    "                MATCH (c:Class {fqn:$fqn})",
    "                MERGE (an:Annotation {name:$name})",
    "                MERGE (c)-[r:ANNOTATED_WITH]->(an)",
    "                SET r.value=$value",
    "            ''', name=a['name'], value=a['value'], fqn=fqn)",
    "",
    "        for fd in cls['fields']:",
    "            fid = f\"{fqn}#{fd['name']}\"",
    "            tx.run('''",
    "                MATCH (c:Class {fqn:$fqn})",
    "                MERGE (fd:Field {id:$id})",
    "                SET fd.name=$name, fd.type=$type",
    "                MERGE (c)-[:HAS_FIELD]->(fd)",
    "            ''', id=fid, name=fd['name'], type=fd['type'], fqn=fqn)",
    "",
    "        for m in cls['methods']:",
    "            sig = f\"{m['name']}({','.join(m['params'])})\"",
    "            mid = f'{fqn}#{sig}'",
    "            tx.run('''",
    "                MATCH (c:Class {fqn:$fqn})",
    "                MERGE (m:Method {id:$id})",
    "                SET m.name=$name, m.returnType=$returnType, m.signature=$sig, m.line=$line",
    "                MERGE (c)-[:HAS_METHOD]->(m)",
    "            ''', id=mid, name=m['name'], returnType=m['returnType'], sig=sig,",
    "                 line=m['line'], fqn=fqn)",
    "",
    "            for a in m['annotations']:",
    "                tx.run('''",
    "                    MATCH (m:Method {id:$mid})",
    "                    MERGE (an:Annotation {name:$name})",
    "                    MERGE (m)-[r:ANNOTATED_WITH]->(an)",
    "                    SET r.value=$value",
    "                ''', name=a['name'], value=a['value'], mid=mid)",
    "",
    "            for call in m['calls']:",
    "                target_id = f\"{call['scope']}::{call['name']}/{call['argc']}\"",
    "                tx.run('''",
    "                    MATCH (m:Method {id:$mid})",
    "                    MERGE (t:CallTarget {id:$tid})",
    "                    SET t.name=$name, t.scope=$scope, t.argc=$argc",
    "                    MERGE (m)-[r:CALLS]->(t)",
    "                    ON CREATE SET r.count=1",
    "                    ON MATCH  SET r.count=coalesce(r.count,0)+1",
    "                ''', tid=target_id, name=call['name'], scope=call['scope'],",
    "                     argc=int(call['argc']), mid=mid)",
    "",
    "with driver.session(database=DB_NAME) as s:",
    "    s.execute_write(upsert_graph, ast)",
    "print('graph loaded')",
))

cells.append(code(
    "# 12. 검증 쿼리",
    "with driver.session(database=DB_NAME) as s:",
    "    print('# 노드 수 (라벨별)')",
    "    for r in s.run('MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS n ORDER BY n DESC'):",
    "        print(f\"  {r['l']:15s} {r['n']}\")",
    "",
    "    print('\\n# 관계 수 (타입별)')",
    "    for r in s.run('MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n ORDER BY n DESC'):",
    "        print(f\"  {r['t']:18s} {r['n']}\")",
    "",
    "    print('\\n# AuctionlandController 메서드')",
    "    for r in s.run('''",
    "        MATCH (c:Class {name:'AuctionlandController'})-[:HAS_METHOD]->(m)",
    "        RETURN m.name AS name, m.line AS line, m.returnType AS rt, m.signature AS sig",
    "        ORDER BY line",
    "    '''):",
    "        print(f\"  L{r['line']:>3}  {r['name']:30s}  -> {r['rt']:20s}  {r['sig']}\")",
    "",
    "    print('\\n# 메서드 호출 (CALLS)')",
    "    for r in s.run('''",
    "        MATCH (m:Method)-[r:CALLS]->(t:CallTarget)",
    "        RETURN m.name AS caller, t.scope AS scope, t.name AS callee, r.count AS cnt",
    "        ORDER BY caller, callee",
    "    '''):",
    "        print(f\"  {r['caller']:30s} -> {r['scope']}.{r['callee']}  (x{r['cnt']})\")",
))

cells.append(md(
    "## 13. Neo4j Browser 시각화",
    "",
    "Neo4j Browser ([https://browser.neo4j.io](https://browser.neo4j.io)) 또는 Aura Console 에서 아래 쿼리 실행:",
    "",
    "```cypher",
    "MATCH (f:File)-[r1:DECLARES]->(c:Class)",
    "OPTIONAL MATCH (c)-[r2:HAS_FIELD]->(fd:Field)",
    "OPTIONAL MATCH (c)-[r3:HAS_METHOD]->(m:Method)",
    "OPTIONAL MATCH (m)-[r4:CALLS]->(t:CallTarget)",
    "OPTIONAL MATCH (c)-[r5:ANNOTATED_WITH]->(ca:Annotation)",
    "OPTIONAL MATCH (m)-[r6:ANNOTATED_WITH]->(ma:Annotation)",
    "OPTIONAL MATCH (f)-[r7:IMPORTS]->(i:Import)",
    "RETURN f, c, fd, m, t, ca, ma, i, r1, r2, r3, r4, r5, r6, r7",
    "```",
    "",
    "특정 메서드의 호출 흐름만:",
    "",
    "```cypher",
    "MATCH (m:Method)-[:CALLS]->(t:CallTarget)",
    "WHERE m.name STARTS WITH 'get'",
    "RETURN m, t",
    "```",
))

cells.append(code(
    "# 종료 — 드라이버 닫기",
    "driver.close()",
    "print('driver closed')",
))


nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote: {NB_PATH}")
print(f"cells: {len(cells)}")
#webhook test2