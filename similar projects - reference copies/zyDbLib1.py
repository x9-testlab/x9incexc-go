#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
	Purpose: General-purpose function library for importing into scripts.
	History:
		- 20191006 JC: Created.
"""
__author__ = "Jim Collier"
__copyright__ = "Copyright 2019, James Collier"
__credits__ = ["Jim Collier"]
__license__ = "GPL v3.0"
__version__ = "0.9.0"
__maintainer__ = "Jim Collier"
__status__ = "Production"  # Prototype, Development, Production

## Import generic function library
import os, sys, pathlib

## Imports; custom librar[y|ies]
meFilespec=os.path.realpath(__file__)
meDir=str(pathlib.Path(meFilespec).parent)
meInclude=meDir + "/0_include"
if meDir not in str(sys.path):
	sys.path.insert(1, meDir)  ## Include current execution path in search path
if pathlib.Path(meInclude).is_dir():
	if meInclude not in str(sys.path):
		sys.path.insert(1, meInclude)  ## Include current execution path in search path
import zy0Lib1 as z


def _unitTests():
	##	History:
	##		- 20191006 JC: Created.
	z.echo_clean()
	z.echo("Unit tests")

	z.printUnitTestFlowerbox("SqlStr")
	sqlString=SqlStr()
	sqlString.addLine(  "CREATE TABLE IF NOT EXISTS filesys ("  )
	sqlString.addLine(  "	id                                            INTEGER PRIMARY KEY AUTOINCREMENT,"  )
	sqlString.addLine(  "	hostname                                      TEXT NOT NULL,"  )
	sqlString.addLine(  "	path_prefix                                   TEXT NOT NULL,"  )
	sqlString.addLine(  "	row_inserted_utc                              TEXT DEFAULT CURRENT_TIMESTAMP,"  )
	sqlString.addLine(  "	comment                                       TEXT,"  )
	sqlString.addLine(  ");"  )
	sqlString.addLine(  ""  )
	sqlString.addLine(  "CREATE UNIQUE INDEX IF NOT EXISTS uidx1 ON filesys ( hostname, path_prefix );"  )
	sqlString.addLine(  "CREATE        INDEX IF NOT EXISTS idx1  ON filesys ( hostname );"  )
	sqlString.addLine(  "CREATE        INDEX IF NOT EXISTS idx1  ON filesys ( path_prefix );"  )
	sqlString.addLine(  "CREATE        INDEX IF NOT EXISTS idx1  ON filesys ( row_inserted_utc );"  )
	z.echo_clean()
	z.echo_clean("Friendly:\n" + sqlString.get(friendly=True))
	z.echo_clean()
	z.echo_clean("Useful:\n" + sqlString.get())

	z.echo_clean()




######################################################################
##	SqlStr
##
##	Purpose:
##		- A handy and thin layer on top of SQL.
##		- Mostly just string handling/sanitizing.
##	History:
##		- 20191006 JC: Created.
######################################################################

class SqlStr:

	def __init__(self):
		self.isDirty=False
		self.sqlList = []
		self.sql_Friendly=""
		self.sql_Useful=""
		import re
		self.regex=re

	def addLine(self, arg: str):
		self.isDirty=True
		self.sqlList.append(arg)

	def get(self, friendly=False):
		self._clean()
		if friendly:
			return self.sql_Friendly
		else:
			return self.sql_Useful

	def _clean(self):
		if self.isDirty:
			self.sql_Friendly=""
			self.sql_Useful=""
			if len(self.sqlList) > 0:
				self.sql_Friendly="\n".join(self.sqlList) #.....................................: Join list together with newlines in between
				self.sql_Friendly=self.regex.sub(r",(\s*\))", r"\1", self.sql_Friendly) #.......: Required: Remove last comma before closing parenthesis, which would cause statement to fail (but makes editing SQL statements much easier)
				self.sql_Friendly=self.regex.sub(r",(\s*;)", r"\1", self.sql_Friendly) #........: Required: Remove last comma before semicolon, which would cause statement to fail (but makes editing SQL statements much easier)
				self.sql_Friendly=self.regex.sub(r",(\s*FROM)", r"\1", self.sql_Friendly) #.....: Required: Remove last comma before 'FROM', which would cause statement to fail (but makes editing SQL statements much easier)
				self.sql_Friendly=self.regex.sub(r",(\s*WHERE)", r"\1", self.sql_Friendly) #....: Required: Remove last comma before 'WHERE', which would cause statement to fail (but makes editing SQL statements much easier)
				self.sql_Friendly=self.sql_Friendly.replace(" )", ")") #........................: Non-required prettify: Remove space after opening parenthesis.
				self.sql_Friendly=self.sql_Friendly.replace("( ", "(") #........................: Non-required prettify: Remove space after opening parenthesis.
				self.sql_Friendly=self.sql_Friendly.replace(" ;", ";") #........................: Non-required prettify: Remove space after opening parenthesis.
				self.sql_Friendly=self.sql_Friendly.replace("\t", "    ") #.....................: Non-required prettify: Replace tabs with 4 spaces.
				self.sql_Useful=z.strNormalize(self.sql_Friendly)
				self.sql_Useful=self.sql_Useful.replace(" )", ")") #............................: Non-required prettify: Remove space after opening parenthesis.
				self.sql_Useful=self.sql_Useful.replace("( ", "(") #............................: Non-required prettify: Remove space after opening parenthesis.
			self.isDirty=False




######################################################################
##	ZsqlLite3, Zsqlite3_zCursor
##
##	Purpose:
##		- Abstracts sqlite3 interface.
##		- Tries to fix the leaky mess that was v2, by abstracting fewer things and just focusing on the good.
##		- The good parts of v2:
##			- connection.row_factory=sqlite3.Row on init.
##			- Trying to turn off auto transaction on init.
##		 		- getTopLeftValViaSql() is pretty handy.
##			- runSql()'s ability to determine whether to run execute() or executescript().
##			- runSql() from either connection object or cursor.
##			- getRowCountViaSql() [via SQL]
##			- Handling tuples for parameterized queries.
##			- createDb() vs openDb() vs openOrCreateDb()
##			- Throws error if you try to fetch*() on a call to runSql() that had multiple statement. (Which means you have to call executescript() instead of execute(), which means no rows can be returned.)
##			- Throws an error if you try to count rows, without having called fetch*()
##		- The bad parts of v2:
##			- Wrapping transaction handling (other than turning off auto transactions on it).
##			- Returning a cursor vs. row.
##			- Trying to determine row count the easy way.
##			- Abtracting rows.
##	Notes:
##		- Python's sqlite3 driver is notoriously wonky and inconsistent.
##		- A better "driver" to base this wrapper on, would be APSW
##			https://rogerbinns.github.io/apsw/
##			https://packages.ubuntu.com/search?keywords=python-apsw
##	History:
##		- 20191007 JC: Created by copying and simplifying v2.
######################################################################

class ZsqlLite3:

	def __init__(self, dbSpec=None):
		import sqlite3
		self._sqlite3=sqlite3
		self._dbSpec=dbSpec
		if not self._dbSpec is None:
			self.openOrCreateDb(self._dbSpec)

	def __del__(self):
		try:    self._conn.close()
		except: pass
		self._conn=None
		self._sqlite3=None

	def createDb(self, dbSpec=""):
		##	Arguments:
		##		dbSpec ....: A file specification, :memory: style syntax, or nothing for tempdb.
		##	Returns: (nothing)
		if not z.isEmpty(dbSpec): ## Blank is OK for a temp DB.
			if dbSpec != ":memory:":
				if z.doesPathExist(dbSpec):
					raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Database file already exists: '" + dbSpec + "'.")
		self.openOrCreateDb(dbSpec)

	def openDb(self, dbSpec=""):
		##	Arguments:
		##		dbSpec ....: A file specification, :memory: style syntax, or nothing for tempdb.
		##	Returns: (nothing)
		if not z.isEmpty(dbSpec): ## Blank is OK for a temp DB.
			if dbSpec != ":memory:":
				if not z.doesPathExist(dbSpec):
					raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Database file not found: '" + dbSpec + "'.")
		self.openOrCreateDb(dbSpec)

	def openOrCreateDb(self, dbSpec=""):
		##	Arguments:
		##		dbSpec ....: A file specification, :memory: style syntax, or nothing for tempdb.
		##	Returns: (nothing)
		self._dbSpec=dbSpec
		self._conn=self._sqlite3.connect(self._dbSpec)
		self._conn.row_factory=self._sqlite3.Row
		self._conn.isolation_level = None  ## Gain more control over transactions; 'executescript()' still issues a 'COMMIT' before running though.
		self._conn.executescript("pragma foreign_keys") ## Enable foreign key support

	def getRowCountViaSql(self, tableName: str, idColName="rowid", whereClause=""):
		sql="SELECT count({}) FROM {}".format(idColName, tableName)
		if not z.isEmpty(whereClause):
			whereClause=str(whereClause)
			if not "where" in whereClause.lower():
				sql += " WHERE "
			sql += " " + whereClause
		sql += ";"
		sql=z.strNormalize(sql)
		return self.getTopLeftValViaSql(sql, castToType=z.TYPE_INT)

	def getTopLeftValViaSql(self, sql: str, castToType=z.TYPE_UNKNOWN):
		## "Cursor-less", because it creates its own temp cursor
		retVal=None
		cursor=self._conn.cursor()
		cursor.execute(sql)
		rows=cursor.fetchone()
		if not z.isEmpty(rows):
			if len(rows)>0:
				retVal=rows[0]
		retVal=z.cast(retVal, castToType)
		rows=None
		cursor=None
		return retVal

	def runSql(self, sql: str, paramsTuple=None):
		##	Purpose:
		##		- Creates a new ZdbSqlite3v2_zCursor to run SQL on.
		##	Returns: A new ZdbSqlite3v2_zCursor with results, which can be ignored.
		newZcursor=self.zCursor()
		newZcursor.runSql(sql, paramsTuple)
		return newZcursor

	def zCursor(self):
		## Create and return a new custom cursor object
		return Zsqlite3_zCursor(self)

	@property
	def native_sqlite3(self):
		return self._sqlite3

	@property
	def native_connection(self):
		return self._conn

class Zsqlite3_zCursor:

	def __init__(self, parentConn):
		self._parentConn=parentConn
		self._curs=parentConn.native_connection.cursor()
		self._canFetchRows=False
		self._wereRowsFetched=False
		self._fetchedRowCount=0

	def __del__(self):
		True

	def runSql(self, sql: str, paramsTuple=None):
		statementCount=sql.count(";")  ## This determines whether we can run 'execute' or 'executescript'. You can use fetch*() on the former, not on the latter.
		## Reset defaults
		self._canFetchRows=False
		self._wereRowsFetched=False
		self._fetchedRowCount=0
		if not paramsTuple is None:
			if not isinstance(paramsTuple, tuple):
				raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Argument 'paramsTuple' isn't a tuple.")
		if isinstance(paramsTuple, tuple):
			if statementCount<=1:
				self._curs.execute(sql, paramsTuple)
				self._canFetchRows=True
			else:
				raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Python's sqlite3 driver can't process a SQL command that is both multi-statement, AND parameterized with a tuple.")
		else:
			if statementCount<=1:
				self._curs.execute(sql)
				self._canFetchRows=True
			else:
				self._curs.executescript(sql)

	def beginTrans(self):
		self._curs.execute("BEGIN TRANSACTION;")
		return True  ## Basically just so we can indent everything underneath

	def commitTrans(self):
		self._curs.execute("COMMIT TRANSACTION;")

	def rollbackTrans(self):
		self._curs.execute("ROLLBACK TRANSACTION;")

	def fetchAll(self):
		if not self._canFetchRows:
			raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Python's sqlite3 driver can't return rows from a SQL command having multiple statements.")
		else:
			rows=self._curs.fetchall()
			self._wereRowsFetched=True
			self._fetchedRowCount=len(rows)
			return rows

	def fetchOne(self):
		if not self._canFetchRows:
			raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Python's sqlite3 driver can't return rows from a SQL command having multiple statements.")
		else:
			rows=self._curs.fetchone()
			self._wereRowsFetched=True
			self._fetchedRowCount=len(rows)
			return rows

	def fetchMany(self, size: int):
		if not self._canFetchRows:
			raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": Python's sqlite3 driver can't return rows from a SQL command having multiple statements.")
		else:
			rows=self._curs.fetchmany(size)
			self._wereRowsFetched=True
			self._fetchedRowCount=len(rows)
			return rows

	@property
	def fetchedRowCount(self):
		if not self._wereRowsFetched:
			raise ValueError(z.getMeName(sys._getframe().f_code.co_name) + ": No rows were fetched yet via 'fetch[All|One|Many](), so there's no way to know the record count this way.")
		else:
			return self._fetchedRowCount

	@property
	def canFetchRows(self):
		return self._canFetchRows

	@property
	def native_cursor(self):
		return self._curs




######################################################################
## Script init
######################################################################

## Execute _unitTests() if not imported
if __name__ == "__main__":
	_unitTests()
