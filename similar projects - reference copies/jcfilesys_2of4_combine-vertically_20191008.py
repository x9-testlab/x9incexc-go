#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
	Purpose: Updates a normalized master sqlite3 database, with corrected data from individual source scan DBs.
	History:
		- 20191006 JC: Created.
		- 20191007 JC:
			- Fixed index creation name collisions (and removed 'IF NOT EXIST' so I'll know about failure).
			- Got rid of all "CREATE IF NOT EXIST" clauses. Want to fail if exists.
			- Replace ❴squote❵ with ' in filename and xattrs.
			- Update xattrs to fix missing quotes in rmlint.*.
"""

__author__ = "Jim Collier"
__copyright__ = "Copyright 2019, James Collier"
__credits__ = ["Jim Collier"]
__license__ = "GPL v3.0"
__version__ = "0.9.0"
__maintainer__ = "Jim Collier"
__status__ = "Development"  # Prototype, Development, Production

## Imports; standard libarary
import os, sys, pathlib, logging, re, time

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
import zyDbLib1 as zdb

## Logging
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
#logging.debug("os.getcwd() = '{}'".format(os.getcwd()))

## Options
#sys.tracebacklimit = 1

def main(*args):

	try:

		## Constants
		SERIALDT=z.getSerialDateTime1()
		if   z.isDir("/home/collierjr/0-0/data/projects/bigdata/checksums"):
			BASEPATH="/home/collierjr/0-0/data/projects/bigdata/checksums"
		elif z.isDir("/mnt/dev/sda1/j.filesys_log"):
			BASEPATH="/mnt/dev/sda1/j.filesys_log"

		## Variables
		newDb_Path="{}/{}_{}.sqlite3".format(BASEPATH, "jcfilesys_2of4_combined-vertically", SERIALDT)
		
		## Init

	#	## Remove newDb_zConn (since we're recreating it anyway)
	#	import os
	#	if ((not z.isEmpty(newDb_Path)) and z.doesPathExist(newDb_Path)): os.remove(newDb_Path)
	
		## Show info and prompt to continue
		z.echo_clean1()
		z.echo_clean1("Database to create from individual source b12, b13, and b15 sources: '" + newDb_Path + "'")
		z.echo_clean1()
		z.promptToContinue1()
		z.echo1()

		######################################################################
		## Makeitso
		######################################################################

		## Create newDb object
		newDb_zConn=zdb.ZdbSqlLite3v3()
		newDb_zConn.createDb1(newDb_Path)

		## Create and seed newDb_zConn
		z.echo1("Creating and seeding newDb_zConn ...")
		newDb_zConn.runSql(sql_Create_newDb())
		newDb_zConn.runSql(sql_Seed_newDb())

		## Process each input file
		process(newDb_zConn, "b12", 1, 1, "{}/{}".format(BASEPATH, "j.filesys_log_b12_za09_20190924-031000.sqlite3"))
		process(newDb_zConn, "b13", 2, 2, "{}/{}".format(BASEPATH, "j.filesys_log_b13_zp4_20190924-031200.sqlite3"))
		process(newDb_zConn, "b15", 3, 3, "{}/{}".format(BASEPATH, "j.filesys_log_b15_ba07_20190925-0504_complete.sqlite3"), "0_xfer/inbound/20190727_from_zp4/")

	except:
		if z.ignoreError:
			z.ignoreError=False
		else:
			raise
	else:
		z.echo1()
		z.echo1("Success.")
	finally:
		newDb_zConn=None
		z.echo1("Done.")
		z.echo1()


def process(newDb_zConn, hostname: str, filesys_id: int, batch_id: int, oldDb_Path: str, pathSubStr=""):

		z.echo1()
		z.echo1("Processing '" + hostname + "' database ...")

		LEN_REMOVE_FROM_PREFIX=len(pathSubStr)

		sqlWhere=""
		if not z.isEmpty(pathSubStr):
			sqlWhere="WHERE path_rltv LIKE '{}%'".format(pathSubStr)

		## Query records from old aka source
		z.echo1("Querying ...")
		oldDb_zConn=zdb.ZdbSqlLite3v3()
		oldDb_zConn.openDb1(oldDb_Path)
		oldDb_zCurs=oldDb_zConn.runSql(sql_OldDb(sqlWhere))
		z.echo1("Loading results into memory ...")
		oldDb_Rows=oldDb_zCurs.fetchAll()
		oldDbRowCount=oldDb_zCurs.fetchedRowCount

		if oldDbRowCount<=0:
			raise ValueError(z.getMeName1(sys._getframe().f_code.co_name) + ": No old [aka source] records to process.")
		else:
		
			## Top of loop init
			z.echo1("Iterating through records ...")
			currentRowNumber=0
			progress=z.Progress1(oldDbRowCount, "rows", 2)
			persistent_sql_InsertIntoNew=sql_InsertIntoNew()
			prev_valNew_path_rltv=""
			skippedoldDbRowCount=0

			## Prepare new DB for insertions
			newDb_zCurs=newDb_zConn.zCursor()
			if newDb_zCurs.beginTrans():

				## Iterate over old aka source records
				for oldDbRow in oldDb_Rows:
					currentRowNumber+=1
					progress.print(currentRowNumber)

					## Get existing values
					valOld_path_rltv        = oldDbRow["depr_path_rltv_escaped"]
					valOld_content_blake2   = oldDbRow["depr_content_blake2b_hex"]
					valOld_xattrs           = z.cast1(oldDbRow["xattrs"], z.TYPE_STR)

					## Debuggable
					if not z.isEmpty(valOld_xattrs):
						True

					## Transform; Unescape relative path
					try:
						valNew_path_rltv=z.unEscapeStr2(valOld_path_rltv)
						valNew_path_rltv=z.doUnescapeStr_Oldstyle1(valNew_path_rltv)
					except:
						valNew_path_rltv="Error un-escaping: '{}'".format(valOld_path_rltv)
						pass

					## Detect sequential duplicate path. (Not sure how this happened. Seems like a bug in the very first 'j.filesys_log' bash script used to generate individual checksum files. Suspect records from that output have identical 'path_rltv', but different original 'path_rltv_blake2', which alone, is unhelpful. We could just let the insert fail with some variation of  'INSERT OR IGNORE INTO', but I want to know about it.
					if (valNew_path_rltv==prev_valNew_path_rltv):
						z.echo_clean_force1()
						z.echo_clean1("    Skipping row due to duplicate path: '{}'".format(valNew_path_rltv))
						time.sleep(0.01)
						skippedoldDbRowCount+=1
					else:

						## Transform; Remove incorrect first part of b15 relative path
						try:
							if LEN_REMOVE_FROM_PREFIX>0:
								if len(valNew_path_rltv)>LEN_REMOVE_FROM_PREFIX:
									valNew_path_rltv=valNew_path_rltv[LEN_REMOVE_FROM_PREFIX:]
						except:
							valNew_path_rltv="Error trimming: '{}'".format(valNew_path_rltv)
							pass

						## Transform; Get new blake2b digest for path; path_rltv_blake2b
						try:
							valNew_path_rltv_blake2b=z.getDigest1_blake2b(valNew_path_rltv, True)
						except:
							valNew_path_rltv_blake2b="Error generating blake2b digest for '{}'".format(valNew_path_rltv)
							pass

						## Transform; old content_blake2b from hex to base64URL
						try:
							valNew_content_blake2b=z.toBase64URL1(valOld_content_blake2)
						except:
							valNew_content_blake2b="Error converting content_blake2b to base64URL: '{}'".format(valOld_content_blake2)
							pass

						## xattrs
						try:
							valNew_xattrs=""
							if not z.isEmpty(valOld_xattrs):
								valNew_xattrs=valOld_xattrs
								valNew_xattrs=z.unEscapeStr2(valNew_xattrs)
								valNew_xattrs=z.doUnescapeStr_Oldstyle1(valNew_xattrs)
								valNew_xattrs=re.sub(r'^user\.rmlint\.(.*)="?([0-9a-f]+)"?$', r'user.rmlint.\1="\2"', valNew_xattrs, flags=(re.IGNORECASE|re.MULTILINE)) #....: Make sure rmlint hex xattrs have quotes around values.
								valNew_xattrs=re.sub(r'^user\.rmlint\.(.*)="?([0-9\.]+)"?$', r'user.rmlint.\1="\2"', valNew_xattrs, flags=(re.IGNORECASE|re.MULTILINE)) #.....: Make sure rmlint mtime xattr has quotes around values.
						except:
							valNew_xattrs="Error unescaping xattrs: '{}'".format(valOld_xattrs)
							pass


						## Insert the record
						tmpList=[]
						tmpList.append(filesys_id)
						tmpList.append(batch_id)
						tmpList.append(valNew_path_rltv_blake2b)
						tmpList.append(valNew_path_rltv)
						tmpList.append(oldDbRow["filesize"])
						tmpList.append(oldDbRow["mtime"])
						tmpList.append(oldDbRow["mtime_tz"])
						tmpList.append(valNew_content_blake2b)
						tmpList.append(valNew_xattrs)
						tmpList.append(oldDbRow["row_inserted_utc"])
						tmpList.append(oldDbRow["depr_path_rltv_escaped"])
						tmpList.append(oldDbRow["depr_path_rltv_escaped_withNL_blake2b_hex"])
						tmpList.append(oldDbRow["depr_content_blake2b_hex"])
						newDb_zCurs.runSql(persistent_sql_InsertIntoNew, paramsTuple=tuple(tmpList))

					## Save previous values for comparison next loop
					prev_valNew_path_rltv=valNew_path_rltv


				## Clean up from loop
				print()  ## To not erase progress output
				z.echo_resetBlank1()

				newDb_zCurs.commitTrans()

				if skippedoldDbRowCount>0:
					z.echo_clean1("    {} records skipped due to duplicate paths.".format(skippedoldDbRowCount))


def sql_InsertIntoNew():
	##	History:
	##		- 20191007 JC: Created.
	sqlStr=zdb.Sql1()
	sqlStr.addLine( "INSERT INTO file ("  )
	sqlStr.addLine( "	filesys_id,"  )
	sqlStr.addLine( "	batch_id,"  )
	sqlStr.addLine( "	path_rltv_blake2b,"  )
	sqlStr.addLine( "	path_rltv,"  )
	sqlStr.addLine( "	filesize,"  )
	sqlStr.addLine( "	mtime,"  )
	sqlStr.addLine( "	mtime_tz,"  )
	sqlStr.addLine( "	content_blake2b,"  )
	sqlStr.addLine( "	xattrs,"  )
	sqlStr.addLine( "	row_inserted_utc,"  )
	sqlStr.addLine( "	depr_path_rltv_escaped,"  )
	sqlStr.addLine( "	depr_path_rltv_escaped_withNL_blake2b_hex,"  )
	sqlStr.addLine( "	depr_content_blake2b_hex,"  )
	sqlStr.addLine( ") VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )"  )
	sqlStr.addLine( ";"  )
	return sqlStr.get()


def sql_OldDb(sqlWhere=""):
	##	History:
	##		- 20191007 JC: Created.
	sqlStr=zdb.Sql1()
	sqlStr.addLine( "SELECT"  )
	sqlStr.addLine( "	size as filesize,"  )
	sqlStr.addLine( "	mtime,"  )
	sqlStr.addLine( "	mtime_tz,"  )
	sqlStr.addLine( "	xattrs,"  )
	sqlStr.addLine( "	row_inserted_utc,"  )
	sqlStr.addLine( "	path_rltv        as depr_path_rltv_escaped,"  )
	sqlStr.addLine( "	path_rltv_blake2 as depr_path_rltv_escaped_withNL_blake2b_hex,"  )
	sqlStr.addLine( "	content_blake2   as depr_content_blake2b_hex,"  )
	sqlStr.addLine( "FROM filesys"  )
	if not z.isEmpty(sqlWhere): sqlStr.addLine(sqlWhere)
	sqlStr.addLine( "ORDER BY path_rltv"  )
	sqlStr.addLine( ";"  )
	return sqlStr.get()


def sql_Copy_oldDb_to_newDb(attachDb_Path: str, host: str, val_filesys_id: int, val_batch_id: int):
	##	History:
	##		- 20191006 JC: Created.
	sqlStr=zdb.Sql1()
	sqlStr.addLine( "ATTACH '" + attachDb_Path + "' AS 'olddb';"  )
	sqlStr.addLine( "INSERT INTO file ( filesys_id             ,         batch_id         ,      path_rltv_blake2b , path_rltv           , filesize , mtime , mtime_tz , content_blake2b , xattrs , row_inserted_utc , depr_path_rltv_escaped , depr_path_rltv_escaped_withNL_blake2b )"  )
	sqlStr.addLine( "SELECT     " + str(val_filesys_id) +     ", " + str(val_batch_id) + ", " + "path_rltv_blake2b , path_rltv_unescaped , size     , mtime , mtime_tz , content_blake2  , xattrs , row_inserted_utc , path_rltv              , path_rltv_pluslf_blake2        FROM olddb.filesys WHERE filesys.hostname='" + host + "' ORDER BY filesys.path_rltv_unescaped;"  )
	sqlStr.addLine( "DETACH 'olddb';"  )
	return sqlStr.get()


def sql_Seed_newDb():
	##	History:
	##		- 20191006 JC: Created.
	sqlStr=zdb.Sql1()
	sqlStr.addLine( "INSERT INTO filesys (  hostname,   path_prefix,                                              row_inserted_utc,      comment )"  )
	sqlStr.addLine( "	VALUES          ( 'b12',      '/mnt/ro/vol/za09/0_mirror/ba07',                         '2019-09-24 10:12:08', 'Although the folder is named ba07, its actually an almost exact clone of zp4.' );"  )
	sqlStr.addLine( "INSERT INTO filesys (  hostname,   path_prefix,                                              row_inserted_utc     )"  )
	sqlStr.addLine( "	VALUES          ( 'b13',      '/mnt/ro/vol/zp4',                                        '2019-09-24 10:12:49' );"  )
	sqlStr.addLine( "INSERT INTO filesys (  hostname,   path_prefix,                                              row_inserted_utc     )"  )
	sqlStr.addLine( "	VALUES          ( 'b15',      '/mnt/ro/vol/ba07/0-0/0_xfer/inbound/20190727_from_zp4',  '2019-09-27 23:27:17' );"  )
	sqlStr.addLine(  ""  )
	sqlStr.addLine( "INSERT INTO batch ( filesys_id,   scan_start_utc,         scan_finish_utc      )"  )
	sqlStr.addLine( "	VALUES        ( 1,           '2019-09-24 10:12:08',  '2019-09-28 01:55:49' );"  )
	sqlStr.addLine( "INSERT INTO batch ( filesys_id,   scan_start_utc,         scan_finish_utc      )"  )
	sqlStr.addLine( "	VALUES        ( 2,           '2019-09-24 10:12:49',  '2019-09-28 01:43:20' );"  )
	sqlStr.addLine( "INSERT INTO batch ( filesys_id,   scan_start_utc,         scan_finish_utc      )"  )
	sqlStr.addLine( "	VALUES        ( 3,           '2019-09-27 23:27:17',  '2019-09-30 03:16:13' );"  )
	return sqlStr.get()


def sql_Create_newDb():
	##	History:
	##		- 20191006 JC: Created.
	sqlStr=zdb.Sql1()

	sqlStr.addLine( "CREATE TABLE filesys ("  )
	sqlStr.addLine( "	id                                            INTEGER PRIMARY KEY AUTOINCREMENT,"  )
	sqlStr.addLine( "	hostname                                      TEXT NOT NULL,"  )
	sqlStr.addLine( "	path_prefix                                   TEXT NOT NULL,"  )
	sqlStr.addLine( "	row_inserted_utc                              TEXT DEFAULT CURRENT_TIMESTAMP,"  )
	sqlStr.addLine( "	comment                                       TEXT,"  )
	sqlStr.addLine( ");"  )
	sqlStr.addLine( "CREATE UNIQUE INDEX uidxA1 ON filesys ( hostname, path_prefix );"  )
	sqlStr.addLine( "CREATE        INDEX  idxA1 ON filesys ( hostname );"  )
	sqlStr.addLine( "CREATE        INDEX  idxA2 ON filesys ( path_prefix );"  )
	sqlStr.addLine( "CREATE        INDEX  idxA3 ON filesys ( row_inserted_utc );"  )
	sqlStr.addLine(  ""  )

	sqlStr.addLine( "CREATE TABLE batch ("  )
	sqlStr.addLine( "	id                                            INTEGER PRIMARY KEY AUTOINCREMENT,"  )
	sqlStr.addLine( "	filesys_id                                    INTEGER NOT NULL,"  )
	sqlStr.addLine( "	scan_start_utc                                TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"  )
	sqlStr.addLine( "	scan_finish_utc                               TEXT,"  )
	sqlStr.addLine( "	FOREIGN KEY(filesys_id) REFERENCES filesys(id) ON UPDATE RESTRICT ON DELETE RESTRICT,"  )
	sqlStr.addLine( ");"  )
	sqlStr.addLine( "CREATE        INDEX  idxB1 ON batch ( filesys_id );"  )
	sqlStr.addLine( "CREATE        INDEX  idxB2 ON batch ( scan_start_utc );"  )
	sqlStr.addLine(  ""  )

	sqlStr.addLine( "CREATE TABLE file ("  )
	sqlStr.addLine( "	id                                            INTEGER PRIMARY KEY AUTOINCREMENT,"  )
	sqlStr.addLine( "	filesys_id                                    INTEGER NOT NULL,"  )
	sqlStr.addLine( "	batch_id                                      INTEGER NOT NULL,"  )
	sqlStr.addLine( "	path_rltv_blake2b                             TEXT NOT NULL,"  )
	sqlStr.addLine( "	path_rltv                                     TEXT NOT NULL,"  )
	sqlStr.addLine( "	filesize                                      INTEGER NOT NULL DEFAULT 0,"  )
	sqlStr.addLine( "	mtime                                         TEXT,"  )
	sqlStr.addLine( "	mtime_tz                                      TEXT,"  )
	sqlStr.addLine( "	content_blake2b                               TEXT,"  )
	sqlStr.addLine( "	xattrs                                        TEXT,"  )
	sqlStr.addLine( "	row_inserted_utc                              TEXT DEFAULT CURRENT_TIMESTAMP,"  )
	sqlStr.addLine( "	xattrs_set_utc                                TEXT,"  )
	sqlStr.addLine( "	depr_path_rltv_escaped                        TEXT,"  )
	sqlStr.addLine( "	depr_path_rltv_escaped_withNL_blake2b_hex     TEXT,"  )
	sqlStr.addLine( "	depr_content_blake2b_hex                      TEXT,"  )
	sqlStr.addLine( "	FOREIGN KEY(filesys_id) REFERENCES filesys(id) ON UPDATE RESTRICT ON DELETE RESTRICT,"  )
	sqlStr.addLine( "	FOREIGN KEY(batch_id) REFERENCES batch(id) ON UPDATE RESTRICT ON DELETE RESTRICT,"  )
	sqlStr.addLine( ");"  )
	sqlStr.addLine( "CREATE UNIQUE INDEX uidxC1 ON file ( filesys_id, batch_id, path_rltv_blake2b );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC1 ON file ( filesys_id );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC2 ON file ( batch_id );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC3 ON file ( path_rltv_blake2b );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC4 ON file ( path_rltv );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC5 ON file ( filesize );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC6 ON file ( mtime );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC7 ON file ( content_blake2b );"  )
	sqlStr.addLine( "CREATE        INDEX  idxC8 ON file ( xattrs );"  )

	return sqlStr.get()


## Execute main() if not imported
if __name__ == "__main__" : main()  # main(parser.parse_args())
