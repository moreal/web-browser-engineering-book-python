class Text:
    def __init__(self, text: str):
        self.text = text


class Tag:
    def __init__(self, tag: str):
        self.tag = tag


def lex(body: str) -> list[Text | Tag]:
    out: list[Text | Tag] = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer:
                out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer))
    return out
