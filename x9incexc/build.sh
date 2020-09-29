#!/bin/bash

##	Purpose: Quick and dirty build script until 'redo' build system implemented.
##	History:
##		- 20200927 JC: Created.


function fBuild(){

	## Flags
	##	CGO_ENABLED=0  .........................: For simple builds
	##	CGO_ENABLED=1  .........................: If external stuff needs to be built, e.g. sqlite3
	##	GOOS=linux GOARCH=amd64
	##	go build
	##	-a  ....................................: Force rebuild
	##	-ldflags '-s -w'  ......................: Strip debugging info
	##	-tags netgo  ...........................: Use built-in net package rather than system
	##	-tags osusergo,netgo  ..................: Use built-in net and user package rather than more powerful system C versions
	##	-ldflags '-w'  .........................: Disable debugging
	##	Static linking
	##		-ldflags '-w -extldflags "-static"'
	##		-ldflags="-extldflags=-static"
	##	Sqlite3
	##		CGO_ENABLED=1 go build -ldflags="-extldflags=-static" -tags sqlite_omit_load_extension
	##		--tags "libsqlite3 linux" ..........: Cross-compile
	##		Help
	##			https://github.com/mattn/go-sqlite3
	##			https://groups.google.com/g/golang-nuts/c/GU6JGc3MzGs/m/f1OHpiQWH5IJ
	##		Examples:
	##			CGO_CFLAGS="-I/Development/sqlcipher/sqlcipher-static-osx/include"
	##			CGO_LDFLAGS="/Development/sqlcipher/sqlcipher-static-osx/osx-libs/libsqlcipher-osx.a -framework Security -framework Foundation"
	##			env CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o app

	## Statically compile Sqlite3
#	export CGO_ENABLED=1
#	export GOOS=linux
#	export GOARCH=amd64
#	export CGO_CFLAGS=
#	export CGO_LDFLAGS="$(realpath "lib/sqlite3_v3310100/obj/x86-64/sqlite3.o")"

	go build -a -ldflags "-linkmode external -extldflags '-static' -s -w -X main.Version=${version} -X main.GitCommitHash=${gitCommitHash} -X main.BuildDateTime=${buildDateTime}" .
#	go build  -ldflags "-s -w -X main.Version=${version} -X main.GitCommitHash=${gitCommitHash} -X main.BuildDateTime=${buildDateTime}"  -o "bin/${exeName}"

}


function fMain(){

	## Args
	local -r version="$1"

	## Validate
	if [[   -z "$(which basename 2>/dev/null || true)" ]]; then fThrowError "Not found in path: 'basename'"; fi
	if [[   -z "$(which dirname  2>/dev/null || true)" ]]; then fThrowError "Not found in path: 'dirname'";  fi
	if [[   -z "$(which pwd      2>/dev/null || true)" ]]; then fThrowError "Not found in path: 'pwd'";      fi
	if [[   -z "$(which go       2>/dev/null || true)" ]]; then fThrowError "Not found in path: 'go'";       fi
	if [[   -z "$(which upx      2>/dev/null || true)" ]]; then fThrowError "Not found in path: 'upx'";      fi
	if [[ ! -f "main.go"                               ]]; then fThrowError "Not found: 'main.go'";          fi
	if [[   -z "${version}"                            ]]; then fThrowError "No version specified.";         fi

	## Constants
	local -r exeName="$(basename "$(pwd)")"
	local -r gitCommitHash="$(git rev-list -1 HEAD)"
	local -r buildDateTime="$(date -u "+%Y%m%dT%H%M%SZ")"

	## Init
	[[ ! -d  bin                               ]] && mkdir  bin
	[[   -f "/tmp/${exeName}_old"              ]] && rm  "/tmp/${exeName}_old"
	[[   -f "bin/${exeName}_old"               ]] && mv  "bin/${exeName}_old"                 "/tmp/"
	[[   -f "bin/${exeName}"                   ]] && mv  "bin/${exeName}"                     "bin/${exeName}_old"
	[[   -f "/tmp/${exeName}_uncompressed_old" ]] && rm  "/tmp/${exeName}_uncompressed_old"
	[[   -f "bin/${exeName}_uncompressed_old"  ]] && mv  "bin/${exeName}_uncompressed_old"    "/tmp/"
	[[   -f "bin/${exeName}_uncompressed"      ]] && mv  "bin/${exeName}_uncompressed"        "bin/${exeName}_uncompressed_old"

	## Clean up dependencies
	fEcho
	fEcho "Tidying ..."
	go mod tidy | ts "    "

	## Format
	fEcho "Formatting ..."
	gofmt -w -s . | ts "    "  ## Or -l instead of -d to only show what files changed.

	## Verify
	fEcho "Verifying ... $(go mod verify)"
	#go mod verify | (grep -iv "all modules verified" || true) ## Don't show anything on success

	## Stastic analysis
	fEcho "Vetting ..."
	go vet . | ts "    "

	## Linting
	fEcho "Linting ..."
	golint . | ts "    "

	## Build
	fEcho "Building ..."
	fEcho
	fBuild

	## Validate
	if [[ ! -f "bin/${exeName}" ]]; then fThrowError "Not found: 'bin/${exeName}'."; fi

	## Compress
	fEcho "Shrinking ..."
	[[   -f "bin/${exeName}"      ]] && mv  "bin/${exeName}"  "bin/${exeName}_uncompressed"
#	upx  -qq --ultra-brute  -o"bin/${exeName}"  "bin/${exeName}_uncompressed"
	upx  -qq                -o"bin/${exeName}"  "bin/${exeName}_uncompressed" | ts "    "
	fEcho

	## Show
	LC_COLLATE="C" ls -lA --color=always --group-directories-first --human-readable --indicator-style=slash --time-style=+"%Y-%m-%d %H:%M:%S" "bin"

	## Test
	fEcho
	fEcho "Test run ..."
	fEcho_Clean "-------------------------------------------------------------------------------"
	"bin/${exeName}"
	fEcho_Clean "-------------------------------------------------------------------------------"
	fEcho_Clean

}


function fThrowError(){
	fEcho_Clean
	if [[ -n "$1" ]]; then
		fEcho_Clean "Error: $*"
	else
		fEcho_Clean "An error occurred."
	fi
	fEcho_Clean
	exit 1
}


declare -i _wasLastEchoBlank=0
function fEcho_ResetBlankCounter(){ _wasLastEchoBlank=0; }
function fEcho_Clean(){
	if [[ -n "$1" ]]; then
		echo -e "$*" | echo -e "$*"
		_wasLastEchoBlank=0
	else
		[[ $_wasLastEchoBlank -eq 0 ]] && echo
		_wasLastEchoBlank=1
	fi
}
function fEcho(){
	if [[ -n "$*" ]]; then fEcho_Clean "[ $* ]"
	else fEcho_Clean ""
	fi
}
# shellcheck disable=2120  ## References arguments, but none are ever passed; Just because this library function isn't called here, doesn't mean it never will in other scripts.
function fEcho_Force()       { fEcho_ResetBlankCounter; fEcho "$*";       }
function fEcho_Clean_Force() { fEcho_ResetBlankCounter; fEcho_Clean "$*"; }


set -e
set -E
fMain  "$1"  "$2"  "$3"  "$4"  "$5"  "$6"  "$7"  "$8"  "$9"