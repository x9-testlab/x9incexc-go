#!/bin/bash

##	Purpose: Quick and dirty build script until 'redo' build system implemented.
##	History:
##		- 20200927 JC: Created.


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
#	local -r exeName="$(basename "$(dirname "$(pwd)")")"
	local -r gitCommitHash="$(git rev-list -1 HEAD)"
	local -r buildDateTime="$(date -u "+%Y%m%dT%H%M%SZ")"

	## Init
	[[ ! -d  bin                  ]] && mkdir  bin
	[[   -f "/tmp/${exeName}_old" ]] && rm    "/tmp/${exeName}_old"
	[[   -f "bin/${exeName}_old"  ]] && mv    "bin/${exeName}_old"  "/tmp/"
	[[   -f "bin/${exeName}"      ]] && mv    "bin/${exeName}"      "bin/${exeName}_old"

	## Clean up dependencies
	echo "[ Tidying ... ]"
	go mod tidy
	echo "[ Verifying ... ]"
	go mod verify
	#go mod verify | (grep -iv "all modules verified" || true) ## Don't show anything on success

	## Format
	echo "[ Formatting ... ]"
	gofmt -w -s .  ## Or -l instead of -d to only show what files changed.

	## Stastic analysis
	echo "[ Vetting ... ]"
	go vet .
	echo "[ Linting ... ]"
	golint .

	## Build
	echo "[ Building ... ]"
	go build  -ldflags "-s -w -X main.Version=${version} -X main.GitCommitHash=${gitCommitHash} -X main.BuildDateTime=${buildDateTime}"  -o "bin/${exeName}"

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


	## Compress
	echo "[ Shrinking ... ]"
	[[   -f "bin/${exeName}"      ]] && mv  "bin/${exeName}"  "bin/${exeName}_uncompressed"
	upx  -qq --ultra-brute  -o"bin/${exeName}"  "bin/${exeName}_uncompressed"

	## Show
	LC_COLLATE="C" ls -lA --color=always --group-directories-first --human-readable --indicator-style=slash --time-style=+"%Y-%m-%d %H:%M:%S" "bin"

	## Test
	echo
	echo "[ Test run ... ]"
	echo "-------------------------------------------------------------------------------"
	bin/${exeName}
	echo "-------------------------------------------------------------------------------"
	echo

}


function fThrowError(){
	echo
	if [[ -n "$1" ]]; then
		echo "Error: $*"
	else
		echo "An error occurred."
	fi
	echo
	exit 1
}


set -e
set -E
fMain  "$1"  "$2"  "$3"  "$4"  "$5"  "$6"  "$7"  "$8"  "$9"