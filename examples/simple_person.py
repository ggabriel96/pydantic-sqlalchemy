import json

from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

from alchemista import model_from

Base = declarative_base()
engine = create_engine("sqlite://")


class PersonDB(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    age = Column(Integer, default=0, nullable=False, doc="Age in years")
    name = Column(String(128), nullable=False, doc="Full name")


Person = model_from(PersonDB)
print("Schema of generated model:")
print(json.dumps(Person.schema(), indent=4))


Base.metadata.create_all(engine)
SessionMaker = sessionmaker(bind=engine)

person = Person.construct(name="Someone", age=25)
with SessionMaker.begin() as session:  # pylint: disable=no-member
    session.add(PersonDB(**person.dict()))

with SessionMaker.begin() as session:  # pylint: disable=no-member
    person_db = session.execute(select(PersonDB)).scalar_one()
    person = Person.from_orm(person_db)  # type: ignore
    print("Instance of model loaded from database:", person)
