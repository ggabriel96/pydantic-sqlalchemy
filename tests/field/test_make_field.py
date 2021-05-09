import enum
import time
import datetime as dt

import pytest
from sqlalchemy import ARRAY, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import declarative_base

from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from pydantic_sqlalchemy.field import FieldKwargs


def test_field_kwargs_used_as_info() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        age = Column(Integer, info=FieldKwargs(ge=0))

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test = TestPydantic(id=1, age=1)

    # Assert
    assert test.id == 1
    assert test.age == 1
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "age": {"title": "Age", "minimum": 0, "type": "integer"},
        },
        "required": ["id"],
    }


def test_default_comes_from_column_definition() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        column = Column(String, default="default")

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test = TestPydantic(id=1)

    # Assert
    assert test.id == 1
    assert test.column == "default"
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "column": {"title": "Column", "default": "default", "type": "string"},
        },
        "required": ["id"],
    }


def test_length_comes_from_column_definition() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        string = Column(String(64))

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test = TestPydantic(id=1)

    # Assert
    assert test.id == 1
    assert test.string is None
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "string": {"title": "String", "maxLength": 64, "type": "string"},
        },
        "required": ["id"],
    }


def test_length_from_info_must_match_column_definition() -> None:
    # Arrange
    max_length = 64
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        string = Column(String(max_length), info=dict(max_length=max_length + 1))

    # Act / Assert
    with pytest.raises(ValueError) as ex:
        sqlalchemy_to_pydantic(Test)
    assert str(ex.value) == (
        "max_length (65) differs from length set for column type (64)."
        " Either remove max_length from info (preferred) or set them to equal values"
    )


def test_lambda_as_default_factory() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        dynamic_column = Column(String, default=lambda: "dynamic default")

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test = TestPydantic(id=1)

    # Assert
    assert test.id == 1
    assert test.dynamic_column == "dynamic default"
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "dynamic_column": {"title": "Dynamic Column", "type": "string"},
        },
        "required": ["id"],
    }


def test_datetime_now_as_default_factory() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        datetime = Column(DateTime, default=dt.datetime.now)

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test1 = TestPydantic(id=1)
    time.sleep(0.1)
    test2 = TestPydantic(id=2)

    # Assert
    assert test1.id == 1
    assert isinstance(test1.datetime, dt.datetime)
    assert test2.id == 2
    assert isinstance(test2.datetime, dt.datetime)
    assert test1.datetime < test2.datetime
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "datetime": {"title": "Datetime", "type": "string", "format": "date-time"},
        },
        "required": ["id"],
    }


def test_allow_mutation() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        number = Column(Integer, info=dict(allow_mutation=False))
        number_mut = Column(Integer, info=dict(allow_mutation=True))

    class ValidateAssignment:
        validate_assignment = True

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test, config=ValidateAssignment)
    test = TestPydantic(id=1, number=0, number_mut=1)

    # Assert
    assert test.id == 1
    assert test.number == 0
    assert test.number_mut == 1
    test.number_mut = 2
    assert test.number_mut == 2
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "number": {"title": "Number", "allow_mutation": False, "type": "integer"},
            "number_mut": {
                "title": "Number Mut",
                "allow_mutation": True,
                "type": "integer",
            },
        },
        "required": ["id"],
    }

    with pytest.raises(TypeError):
        test.number = 1
    assert test.number == 0


def test_enum() -> None:
    # Arrange
    Base = declarative_base()

    class Bool(str, enum.Enum):
        FALSE = "F"
        TRUE = "T"

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        boolean = Column(Enum(Bool), default=Bool.TRUE)

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test = TestPydantic(id=1)

    # Assert
    assert test.id == 1
    assert test.boolean == Bool.TRUE
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "boolean": {
                "default": Bool.TRUE,
                "allOf": [{"$ref": "#/definitions/Bool"}],
            },
        },
        "required": ["id"],
        "definitions": {
            "Bool": {
                "title": "Bool",
                "description": "An enumeration.",
                "enum": ["F", "T"],
                "type": "string",
            }
        },
    }


def test_all_pydantic_attributes_from_info() -> None:
    # Arrange
    Base = declarative_base()

    class Test(Base):
        __tablename__ = "test"

        id = Column(Integer, primary_key=True)
        ge_le = Column(Integer, info=dict(ge=0, le=10))
        gt_lt = Column(Integer, info=dict(gt=0, lt=10))
        items = Column(ARRAY(item_type=str), info=dict(min_items=0, max_items=2))
        multiple = Column(Integer, info=dict(multiple_of=2))
        string = Column(
            Text,
            default="",
            nullable=False,
            info=dict(
                alias="text",
                const="",
                description="Some string",
                example="Example",
                max_length=64,
                min_length=0,
                regex=r"\w+",
                title="SomeString",
            ),
        )

    # Act
    TestPydantic = sqlalchemy_to_pydantic(Test)
    test = TestPydantic(id=1, ge_le=0, gt_lt=1, items=[], multiple=2, text="txt")

    # Assert
    assert test.id == 1
    assert test.ge_le == 0
    assert test.gt_lt == 1
    assert test.items == []
    assert test.multiple == 2
    assert test.string == "txt"
    assert TestPydantic.schema() == {
        "title": "Test",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "ge_le": {"title": "Ge Le", "minimum": 0, "maximum": 10, "type": "integer"},
            "gt_lt": {
                "title": "Gt Lt",
                "exclusiveMinimum": 0,
                "exclusiveMaximum": 10,
                "type": "integer",
            },
            "items": {
                "title": "Items",
                "minItems": 0,
                "maxItems": 2,
                "type": "array",
                "items": {},
            },
            "multiple": {"title": "Multiple", "multipleOf": 2, "type": "integer"},
            "text": {
                "title": "SomeString",
                "description": "Some string",
                "default": "",
                "maxLength": 64,
                "minLength": 0,
                "pattern": "\\w+",
                "example": "Example",
                "type": "string",
            },
        },
        "required": ["id"],
    }
