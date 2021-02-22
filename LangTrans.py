from yaml import load, SafeLoader
from re import compile as comp, MULTILINE, sub

"""
LangTrans
---------
To customize syntax of any programming language.
"""


def tknoptions(sdef):
    """
    This function extract eachline and replace option from yaml

    :param sdef: Contains token options
    :type spattern: dic
    :return: [eachline_option,replace_option]
    :rtype: list
    """
    oneachline = dict()
    replase = dict()
    for tkname in sdef["tokens"]:
        if tkname in sdef:
            if "eachline" in sdef[tkname]:
                oneachline.update({tkname: sdef[tkname]["eachline"]})
            if "replace" in sdef[tkname]:
                replase.update(
                    {
                        tkname: [
                            (comp(repregex[0]), repregex[1])
                            if 1 < len(repregex)
                            else (comp(repregex[0]), "")
                            for repregex in sdef[tkname]["replace"]
                        ]
                    }
                )
    return [oneachline, replase]


def extract(spattern):
    """
    This function extract contents needed from yaml file with regex

    :param spattern: Dictionary with yaml file details
    :type spattern: dic
    :return: option(replace,eachline),regex,token_names
    :rtype: dic,dic,list
    """
    options = dict()
    regexs = dict()
    tknames = []
    for part, sdef in spattern.items():
        if part[0] == "_":
            sdef["tokens"] = spattern[part[2:]]["tokens"]
        regexs.update({part: comp(sdef["regex"], MULTILINE)})
        options.update({part: tknoptions(sdef)})
        tknames.append(sdef["tokens"])
    return options, regexs, tknames


def matching(patterns, tknames, content):
    """
    This function matches tokens from code with regular expressions

    :param patterns: Dictionary regular expression with its token name
    :type patterns: dict
    :param tknames: Token names
    :type tknames: list
    :param content: Tokens are matched from this
    :type content: str
    :return: Matched tokens only and Full match of regular expression
    :rtype: dic,dic
    """
    tknmatches = dict()
    partmatches = dict()
    for (part, pattern), tknames in zip(patterns.items(), tknames):
        # Part matching
        partmatches[part] = [i.group() for i in pattern.finditer(content)]
        # Token matching
        if len(tknames) == 1:
            tknmatches[part] = [
                {tkname: matches}
                for matches, tkname in zip(pattern.findall(content), tknames)
            ]
            continue
        tknmatches[part] = [
            {tkname: match for match, tkname in zip(matches, tknames)}
            for matches in pattern.findall(content)
        ]
    return tknmatches, partmatches


def settings(spattern):
    """
    This function extract settings from yaml

    :param spattern: Dictionary with yaml file details
    :type spattern: dic
    :return: lop,loplimit
    :rtype: bool,int
    """
    loop = False
    loplimit = 7
    if "settings" in spattern:
        settings = spattern["settings"]
        if "loop" in settings:
            loop = settings["loop"]
        if "looplimit" in settings:
            loplimit = settings["looplimit"]
        if "variables" in settings:
            for part, sdef in spattern.items():
                if part != "settings":
                    rv = sdef["regex"]  # regex with var
                    for varname, rgx in settings["variables"].items():
                        if "<" + varname + ">" in rv:  # regex without var
                            rv = rv.replace("<" + varname + ">", rgx)
                    spattern[part]["regex"] = rv
        del spattern["settings"]
    return loop, loplimit


def run_tknoptions(match, tkname, oneachline, replacer):
    """
        Running eachline and replace options on content extracted

    :param match: content extracted
    :type match: string
    :param oneachline: Contain eachline template of all tokens
    :type oneachline: dic
    :param replace: Contain regex to extract and replace with for all token
    :type replace: dic
    :return: match
    :rtype: string
    """
    if tkname in oneachline:  # For oneachline option
        line = oneachline[tkname]
        match = "\n".join(
            [line.replace("<line>", l) for l in match.split("\n") if l.strip() != ""]
        )
    if tkname in replacer:  # For replace option
        for rgx in replacer[tkname]:
            match = sub(*rgx, match)
    return match


def main(content, slocation, tlocation):
    """
    This is main function convert new syntax to orginal syntax

    :param content: Code with new syntax
    :param slocation: Yaml file location containing regular expression for new syntax
    :param tlocation: Yaml file location containing pattern of original syntax
    :type content: str
    :type slocation: str
    :type tlocation: str
    :return: Return code with original syntax
    :rtype: str
    """
    spattern = load(open(slocation).read(), Loader=SafeLoader)  # Source
    tpattern = load(open(tlocation).read(), Loader=SafeLoader)  # Target
    loop, loplimit = settings(spattern)

    options, regexs, tokens = extract(spattern)
    lopcount = 0
    while 1:
        tknmatches, partmatches = matching(regexs, tokens, content)
        # End if there is no match
        if not any(len(i) != 0 for i in partmatches.values()):
            break
        for part in tknmatches:
            if part[0] != "_":  # Find two regex extract with one pattern
                pattern = tpattern[part]
            else:
                pattern = tpattern[part[2:]]
            for tknmatch, partmatch in zip(tknmatches[part], partmatches[part]):
                temp_pattern = pattern
                for tkname, match in tknmatch.items():
                    match = run_tknoptions(match, tkname, *options[part])
                    # Replacing pattern tokens expression with tokens
                    temp_pattern = temp_pattern.replace(f"<{tkname}>", match)
                # Replacing whole block
                content = content.replace(partmatch, temp_pattern)
        lopcount += 1
        if not loop or lopcount == loplimit:
            break
    return content


if __name__ == "__main__":
    from sys import argv, exit

    if len(argv) == 1 or (len(argv) == 2 and argv[1] == "-h"):
        print("Arg usage: <SoureFileName> <OutputFileName> <SyntaxRepr> <PatternRepr>")
        print("SyntaxRepr,PatternRepr: without extension(.yaml) ")
        exit()
    elif len(argv) < 5:
        print("Error: Insufficient number of arguments")
        exit()
    try:
        targetcode = main(open(argv[1]).read(), argv[3] + ".yaml", argv[4] + ".yaml")
        open(argv[2], "w").write(targetcode)
        print(targetcode)
    except Exception as err:
        print("Error:", err)
