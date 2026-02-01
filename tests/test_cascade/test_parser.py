from browser.css import CSSParser, Declaration


def test_parse_important_declaration():
    decls = CSSParser("color: blue !important;").parse_body()
    assert decls == [Declaration(name="color", value="blue", important=True)]


def test_parse_non_important_declaration():
    decls = CSSParser("color: blue;").parse_body()
    assert decls == [Declaration(name="color", value="blue", important=False)]


def test_parse_mixed_important_declarations():
    decls = CSSParser("color: blue !important; font-size: 14px;").parse_body()
    assert decls == [
        Declaration(name="color", value="blue", important=True),
        Declaration(name="font-size", value="14px", important=False),
    ]
