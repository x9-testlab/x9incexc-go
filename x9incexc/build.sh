#!/bin/bash

##	Purpose: Quick and dirty build script until 'redo' build system implemented.
##	History:
##		- 20200927 JC: Created.


function fMain(){

	## Validate
	if [[   -z "$(which basename 2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'basename'"; echo; exit 1; fi
	if [[   -z "$(which dirname  2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'dirname'";  echo; exit 1; fi
	if [[   -z "$(which pwd      2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'pwd'";      echo; exit 1; fi
	if [[   -z "$(which go       2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'go'";       echo; exit 1; fi
	if [[ ! -f "main.go"                               ]]; then echo; echo "Error: Not found: 'main.go'";          echo; exit 1; fi

	## Constants
	local -r exeName="$(basename "$(dirname "$(pwd)")")"

	## Init
	[[ ! -d  bin                  ]] && mkdir  bin
	[[   -f "/tmp/${exeName}_old" ]] && rm    "/tmp/${exeName}_old"
	[[   -f "bin/${exeName}_old"  ]] && mv    "bin/${exeName}_old"  "/tmp/"
	[[   -f "bin/${exeName}"      ]] && mv    "bin/${exeName}"      "bin/${exeName}_old"

	## Build
	echo
	echo "[ Building ... ]"
	echo
	go build -o "bin/${exeName}"

	## Flags
	##	CGO_ENABLED=0  .........................: For simple builds
	##	CGO_ENABLED=1  .........................: If external stuff needs to be built, e.g. sqlite3
	##	GOOS=linux GOARCH=amd64
	##	go build
	##	-a  ....................................: Force rebuild
	##	-tags netgo  ...........................: Use built-in net package rather than system
	##	-tags osusergo,netgo  ..................: Use built-in net and user package rather than more powerful system C versions
	##	-ldflags '-w'  .........................: Disable debugging
	##	Static linking
	##		-ldflags '-w -extldflags "-static"'
	##		-ldflags="-extldflags=-static"
	##	Sqlite3
	##		CGO_ENABLED=1 go build -ldflags="-extldflags=-static" -tags sqlite_omit_load_extension
	##		--tags "libsqlite3 linux" ..........: Cross-compile
	##		## https://github.com/mattn/go-sqlite3

	## Test
	echo
	echo "[ Test run ... ]"
	echo "-------------------------------------------------------------------------------"
	bin/${exeName}
	echo "-------------------------------------------------------------------------------"
	echo

}


set -e
set -E
fMain