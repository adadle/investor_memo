# coding = utf-8
"""
"""

__author__ = 'Eric Lee'

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import Column, String, Boolean, Integer, DECIMAL, Date, UniqueConstraint
from sqlalchemy.dialects.mysql import insert

import logging

logging.basicConfig(level=logging.INFO)
Base = declarative_base()


class DailyProfitModel(Base):
    __tablename__ = 'daily_profit'

    __table_args__ = (
        UniqueConstraint('data_date', 'channel'),
    )

    id = Column('id', Integer, primary_key=True)
    data_date = Column('data_date', Date)
    channel = Column('channel', String(10))
    is_tx_date = Column('is_tx_date', Boolean)
    profit = Column('profit', )

    def __repr__(self):
        return str([getattr(self, c.name, None) for c in self.__table__.c])


class DailyProfit(object):

    def __init__(self, data_date, channel, is_tx_date, profit):
        self.data_date = data_date
        self.channel = channel
        self.is_tx_date = is_tx_date
        self.profit = profit

    def save(self, session=None):
        stmt = insert(DailyProfitModel).values(data_date=self.data_date, channel=self.channel
                                               , is_tx_date=self.is_tx_date, profit=self.profit) \
            .on_duplicate_key_update(data_date=self.data_date, channel=self.channel)
        result = session.execute(stmt)
        session.commit()
        logging.info("save DailyProfit success, rows %i, date %s", result.rowcount, self.data_date)
