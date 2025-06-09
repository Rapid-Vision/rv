#!/usr/bin/env python3

"""
Extracts documentation from a Python source file and generates Markdown files.

The output is structured for use with the [Nextra site generator](https://nextra.site/).
"""

import argparse
import ast
import io
import sys
import shutil
import os
from abc import ABC, abstractmethod
from typing import Union
import tokenize

DocumentableType = Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]


class Documentation:
    module: ast.Module
    src: list[str]
    docs: list["BaseDoc"]

    comments: dict[int, str]

    def __init__(self, src: str) -> None:
        self.docs = []
        self.module = ast.parse(src)
        self.src = src.split()

        self.comments = dict()

        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok_type, tok_string, start, _, _ in tokens:
            if tok_type == tokenize.COMMENT:
                self.comments[start[0]] = tok_string

    def get_node_comments(self, node: ast.stmt):
        result = ""
        for i in range(node.lineno, node.end_lineno + 1):
            comment = self.comments.get(i)
            if comment is not None:
                result += comment[1:].strip() + "\n"
        return result

    def get_module_md(self) -> str:
        docstring = get_rewritten_docstring(self.module)
        if docstring is None:
            docstring = ""

        return f"# Overview\n\n{docstring}"

    def add_doc(self, doc: "BaseDoc"):
        doc.src = self.src
        doc.docs = self
        self.docs.append(doc)

    def parse_func_argument(self, arg: ast.arg) -> tuple[str, str, str]:
        name = arg.arg
        ann = None
        if arg.annotation:
            ann = ast.unparse(arg.annotation)
        comment = self.get_node_comments(arg)
        return name, ann, comment

    def get_func_args(self, func: ast.FunctionDef) -> list[tuple[str, str, str]]:
        result = []
        for arg in func.args.posonlyargs:
            parsed_arg = self.parse_func_argument(arg)
            result.append(parsed_arg)
        for arg in func.args.args:
            parsed_arg = self.parse_func_argument(arg)
            result.append(parsed_arg)
        for arg in func.args.kwonlyargs:
            parsed_arg = self.parse_func_argument(arg)
            result.append(parsed_arg)

        if func.args.vararg is not None:
            name, ann, comment = self.parse_func_argument(func.args.vararg)
            result.append((f"*{name}", ann, comment))
        if func.args.kwarg is not None:
            name, ann, comment = self.parse_func_argument(func.args.kwarg)
            result.append((f"**{name}", ann, comment))

        return result

    def get_function_markup(self, func: ast.FunctionDef):
        result = ""
        result += "**Description**:\n\n"
        result += get_rewritten_docstring(func)

        result += f"**Signature**:\n\n"
        result += f"```python\n"
        result += get_function_signature(func)
        result += "\n```\n\n"

        result += f"**Arguments**:\n\n"

        for name, ann, comment in self.get_func_args(func):
            if name == "self" or name.startswith("_"):
                continue

            result += f"- **`{name}`**"
            if ann is not None:
                result += f" : `{ann}{{:python}}`"
            if comment != "":
                result += f" — {comment}"
            result += "\n"

        result += "\n"

        if check_function_returns_self(func):
            result += f"**Returns**: `Self{{:python}}`\n\n"
        elif func.returns:
            result += "**Returns**: "
            s = ast.unparse(func.returns)
            result += f"`{s}{{:python}}`\n\n"

        return result

    def extract_docstrings(self) -> "Documentation":
        for node in self.module.body:
            if is_enum_class(node):
                enumDoc = EnumDoc(node)
                self.add_doc(enumDoc)
            elif isinstance(node, ast.ClassDef):
                classDoc = ClassDoc(node)
                self.add_doc(classDoc)
            elif isinstance(node, ast.FunctionDef):
                functionDoc = FunctionDoc(node)
                self.add_doc(functionDoc)
        return self

    def save(
        self,
        outdir: str,
    ):
        if os.path.exists(outdir):
            shutil.rmtree(outdir)
        os.makedirs(outdir, exist_ok=True)

        dirs = set(map(lambda d: d.dir_name(), self.docs))
        for d in dirs:
            os.makedirs(os.path.join(outdir, d), exist_ok=True)

        with open(os.path.join(outdir, "index.mdx"), "w") as fout:
            fout.write(self.get_module_md())

        for d in self.docs:
            if d.get_name().startswith("_"):
                continue
            md = d.get_md()
            if md is not None:
                with open(
                    os.path.join(outdir, d.dir_name(), f"{d.get_name()}.mdx"), "w"
                ) as fout:
                    fout.write(md)


class BaseDoc(ABC):
    node: DocumentableType
    docs: Documentation
    src: list[str]

    def __init__(self, node: DocumentableType) -> None:
        self.node = node

    def get_name(self) -> str:
        return self.node.name

    @abstractmethod
    def get_md(self) -> Union[str, None]:
        pass

    @abstractmethod
    def dir_name(self) -> str:
        pass


class ClassDoc(BaseDoc):
    def get_base_classes_list(self):
        return [ast.unparse(base) for base in self.node.bases]

    def get_public_methods(self):
        return [
            method
            for method in self.node.body
            if isinstance(method, ast.FunctionDef) and not method.name.startswith("_")
        ]

    def get_public_attribtues(self):
        return [
            assign
            for assign in self.node.body
            if isinstance(assign, ast.AnnAssign)
            and not assign.target.id.startswith("_")
        ]

    def get_md(self) -> Union[str, None]:
        result = f"# {self.node.name}\n\n"

        base_classes = self.get_base_classes_list()
        if base_classes != []:
            result += "**Inherits from**: " + ", ".join(base_classes) + "\n\n"

        docstring = get_rewritten_docstring(self.node)
        if docstring is not None:
            result += docstring + "\n\n"

        methods = self.get_public_methods()
        attributes = self.get_public_attribtues()

        if len(methods) == 0 and len(attributes) == 0:
            return None

        if len(methods) > 0:
            result += "## Methods\n"
            for method in methods:
                result += f"### `{method.name}`\n"
                result += self.docs.get_function_markup(method)

                result += "---\n"

        if len(attributes) > 0:
            result += "## Attributes\n"
            for assign in attributes:
                annotation = ast.unparse(assign.annotation)
                result += (
                    f"### `{assign.target.id}`\nType: `{annotation}{{:python}}`\n\n"
                )
                result += self.docs.get_node_comments(assign) + "\n"
                result += "---\n"

        return result

    def dir_name(self):
        return "Classes"


class FunctionDoc(BaseDoc):
    def get_md(self) -> Union[str, None]:
        result = f"# {self.node.name}\n\n"
        result += self.docs.get_function_markup(self.node)

        return result

    def dir_name(self):
        return "Functions"


class EnumDoc(BaseDoc):
    def get_md(self) -> Union[str, None]:
        result = f"# {self.node.name}\n\n"
        docstring = get_rewritten_docstring(self.node)
        if docstring is not None:
            result += docstring + "\n\n"

        result += "## Variants\n\n"
        for n in self.node.body:
            if isinstance(n, ast.Assign):
                result += f"### `{n.targets[0].id}`\n"

                result += self.docs.get_node_comments(n)

        return result

    def dir_name(self):
        return "Enums"


def is_enum_class(class_node) -> bool:
    """Check if a class inherits from Enum (by name)."""
    if not isinstance(class_node, ast.ClassDef):
        return False

    for base in class_node.bases:
        # class X(Enum)
        if isinstance(base, ast.Name) and base.id == "Enum":
            return True

        # class X(enum.Enum)
        if isinstance(base, ast.Attribute) and base.attr == "Enum":
            return True
    return False


def get_rewritten_docstring(node):
    """Get node docstring with additional codeblocks annotation"""

    doc = ast.get_docstring(node)
    if doc is None:
        return ""

    s = doc.split("```")
    res = ""
    for i in range(len(s) - 1):
        res += s[i]
        res += "```"
        if i % 2 == 0:
            res += "python copy showLineNumbers"
    res += s[-1]
    return res + "\n\n"


def check_function_returns_self(func: ast.FunctionDef) -> bool:
    cnt = 0
    for stmt in func.body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Return):
                if not isinstance(node.value, ast.Name):
                    return False
                cnt += 1

    if cnt == 0:
        return False  # Returns only None
    else:
        return True


def get_function_signature(node: ast.FunctionDef) -> str:
    new_node = ast.FunctionDef(
        name=node.name,
        args=node.args,
        body=[],  # remove the body
        decorator_list=node.decorator_list,
        returns=node.returns,
        type_comment=node.type_comment,
    )
    new_node.lineno = 0
    return ast.unparse(new_node)[:-1]


def extract_docs(codepath: str, outdir: str) -> None:
    try:
        with open(codepath, "r", encoding="utf-8") as fin:
            source_code = fin.read()
    except FileNotFoundError:
        print(f"File not found: {codepath}", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    Documentation(source_code).extract_docstrings().save(outdir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--code",
        help="Path to the Python source file from which to extract documentation.",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        help="Directory where the generated documentation will be saved. Warning: this directory will be deleted before export.",
    )
    args = parser.parse_args()

    extract_docs(
        codepath=args.code,
        outdir=args.outdir,
    )
