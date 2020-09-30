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
	##	-ldflags '-s -w'  ......................: Strip debugging symbols
	##	-tags netgo  ...........................: Use built-in net package rather than system
	##	-tags osusergo,netgo  ..................: Use built-in net and user package rather than more powerful system C versions
	##	Static linking
	##		-ldflags '-extldflags "-static"'
	##		-ldflags="-extldflags=-static"
	##	Sqlite3
	##		Go flags
	##			CGO_ENABLED=1 go build -ldflags="-extldflags=-static" -tags sqlite_omit_load_extension
	##			--tags "libsqlite3 linux" ..........: Cross-compile and include sqlite3 library.
	##		Help
	##			https://golang.org/cmd/link/
	##			https://github.com/mattn/go-sqlite3
	##			https://groups.google.com/g/golang-nuts/c/GU6JGc3MzGs/m/f1OHpiQWH5IJ
	##			https://golang.org/cmd/cgo/
	##			https://www.ardanlabs.com/blog/2013/08/using-c-dynamic-libraries-in-go-programs.html
	##			https://renenyffenegger.ch/notes/development/languages/C-C-plus-plus/GCC/create-libraries/index
	##			https://akrennmair.github.io/golang-cgo-slides/#1
	##			https://github.com/mattn/go-sqlite3/issues/858
	##			https://www.sqlite.org/compile.html#default_wal_synchronous
	##		Random examples, not sure what works or doesn't:
	##			CGO_CFLAGS="-I/Development/sqlcipher/sqlcipher-static-osx/include"
	##			CGO_LDFLAGS="/Development/sqlcipher/sqlcipher-static-osx/osx-libs/libsqlcipher-osx.a -framework Security -framework Foundation"
	##			env CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o app
	##		Notes:
	##			Instead of ":memory:", which is racey, use "file::memory:?cache=shared". https://github.com/mattn/go-sqlite3

	## Statically compile Sqlite3
#	declare -r GOOS=linux
#	declare -r GOARCH=amd64
	declare -r CGO_ENABLED=1
	
	## Sqlite3 compile-time flags; possibly have no effect in golang (unless using it to compile sqlite3 into program from source), but just in case:
	local sqlite3CompileFlags=""
	sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_OMIT_LOAD_EXTENSION"  #................: Solves a Go problem related to static linking.
	sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_DEFAULT_FOREIGN_KEYS=1"  #.............: 1=Enable foreign key constraints by defualt. (0 is default only for backward compatibility.)
	sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_THREADSAFE=0"  #.......................: 0=single-threaded, 1=fully multithreaded, 2=multithreaded but only one db connection at a time. Default=1, Sqlite3 recommended=0.
	sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_DEFAULT_WAL_SYNCHRONOUS=1"  #..........: Sqlite3 recommended (faster than default and safe).
	sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_DEFAULT_LOCKING_MODE=1"  #.............: 1=Exclusive lock. Usually no reason not to, for 1db per 1app.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_DQS=0"  #..............................: Sqlite3 recommended. Disables the double-quoted string literal misfeature, originally intended to be compatible with older MySql databases.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_DEFAULT_MEMSTATUS=0"  #................: Sqlite3 recommended. causes the sqlite3_status() to be disabled. Speeds everything up.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_LIKE_DOESNT_MATCH_BLOBS"  #............: Sqlite3 recommended. Speeds up LIKE and GLOB operators.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_MAX_EXPR_DEPTH=0"  #...................: Sqlite3 recommended. Simplifies the code resulting in faster execution, and helps the parse tree to use less memory.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_OMIT_DEPRECATED"  #....................: Sqlite3 recommended.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_OMIT_PROGRESS_CALLBACK"  #.............: Sqlite3 recommended.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_OMIT_SHARED_CACHE"  #..................: Sqlite3 recommended. Speeds up.
    sqlite3CompileFlags="${sqlite3CompileFlags} -DSQLITE_USE_ALLOCA"  #.........................: Sqlite3 recommended. Make use of alloca() if exists.
	sqlite3CompileFlags="$(fStrNormalize_byecho "${sqlite3CompileFlags}")"  #...................: Normalize string
	
	## CGo compiler flags
	declare CGO_CFLAGS=""
	CGO_CFLAGS="${CGO_CFLAGS} "
	CGO_CFLAGS="$(fStrNormalize_byecho "${CGO_CFLAGS}")"  #.........: Normalize string

	## CGo linker flags
	declare CGO_LDFLAGS=""
	CGO_LDFLAGS="${CGO_LDFLAGS} "
	CGO_LDFLAGS="$(fStrNormalize_byecho "${CGO_LDFLAGS}")"  #.........: Normalize string

	## -ldflags
	local ldFlags=""
	ldFlags="${ldFlags} -s -w"  #.........................................................: Disable debugging symbols.
#	ldFlags="${ldFlags} -I'$(realpath "lib/sqlite3_v3310100/obj/x86-64/sqlite3.o")'"  #...: Explicitly link in existing .o file
	ldFlags="${ldFlags} -X main.Version=${version}"  #....................................: Inject value
	ldFlags="${ldFlags} -X main.GitCommitHash=${gitCommitHash}"  #........................: Inject value
	ldFlags="${ldFlags} -X main.BuildDateTime=${buildDateTime}"  #........................: Inject value
#	ldFlags="${ldFlags} -H=windowsgui"  #.................................................: No console in Windows
	ldFlags="${ldFlags} -linkmode external"  #............................................: Options: internal, external, auto (external for static linking?)
	ldFlags="${ldFlags} -extldflags '-static'"  #.........................................: Flags to external linker (?)
	ldFlags="$(fStrNormalize_byecho "${ldFlags}")"  #.....................................: Normalize string

	## General Go tags
	local goTags=""
#	goTags="${goTags} linux"  #.......................: Specify cross-compile environment
#	goTags="${goTags} netgo"  #.......................: Use built-in network library, rather than C's (C versions have more features but require gcc and CGO_ENABLED=1).
#	goTags="${goTags} osusergo"  #....................: Use built-in user library, rather than C's (C versions have more features but require gcc and CGO_ENABLED=1).
	goTags="$(fStrNormalize_byecho "${goTags}")"  #...: Normalize string

	## go-sqlite3 Tags
	local goTags_Sqlite3=""
	goTags_Sqlite3="${goTags_Sqlite3} libsqlite3"  #..................................: Statically link in system's libsqlite3 (I think?)
	goTags_Sqlite3="${goTags_Sqlite3} sqlite_omit_load_extension"  #..................: Solves a Go problem related to static linking.
	goTags_Sqlite3="${goTags_Sqlite3} sqlite_foreign_keys=1"  #.......................: 1=Enable foreign key constraints by defualt. (0 is default only for backward compatibility.)
#	goTags_Sqlite3="${goTags_Sqlite3} sqlite_fts5"  #.................................: Version 5 of the full-text search engine (fts5) is added to the build
#	goTags_Sqlite3="${goTags_Sqlite3} sqlite_json  #..................................: 
	goTags_Sqlite3="${goTags_Sqlite3} sqlite_icu"  #..................................: Unicode
	goTags_Sqlite3="$(fStrNormalize_byecho "${goTags_Sqlite3}")"  #...: Normalize string

	## Gather up gotags
	goTags="${goTags} ${goTags_Sqlite3}"
	goTags="$(fStrNormalize_byecho "${goTags}")"  #...: Normalize string

	## Export
	export GOOS
	export GOARCH
	export CGO_ENABLED
	export CGO_CFLAGS
	export CGO_LDFLAGS

	fEcho_Clean
	fEcho_Clean_If "GOOS .................................: " "${GOOS}"
	fEcho_Clean_If "GOARCH ...............................: " "${GOARCH}"
	fEcho_Clean_If "CGO_ENABLED ..........................: " "${CGO_ENABLED}"
	if [[ -n "${CGO_CFLAGS}"           ]]; then fEcho_Clean; fEcho_Clean "CGO_CFLAGS:";                          fEcho_Clean "${CGO_CFLAGS}";            fi
	if [[ -n "${CGO_LDFLAGS}"          ]]; then fEcho_Clean; fEcho_Clean "CGO_LDFLAGS:";                         fEcho_Clean "${CGO_LDFLAGS}";           fi
	if [[ -n "${ldFlags}"              ]]; then fEcho_Clean; fEcho_Clean "ldFlags:";                             fEcho_Clean "--ldflags \"${ldFlags}\""; fi
	if [[ -n "${goTags} "              ]]; then fEcho_Clean; fEcho_Clean "Tags:";                                fEcho_Clean "--tags \"${goTags}\"";     fi
	if [[ -n "${sqlite3CompileFlags} " ]]; then fEcho_Clean; fEcho_Clean "Ideal sqlite3 C compile flags (FYI):"; fEcho_Clean "${sqlite3CompileFlags}";   fi
	fEcho_Clean

	go build --tags "${goTags}" --ldflags "${ldFlags}" .
#	go build -a -ldflags "-linkmode external -extldflags '-static' -s -w -X main.Version=${version} -X main.GitCommitHash=${gitCommitHash} -X main.BuildDateTime=${buildDateTime}" .
#	go build -a -ldflags "-s -w -X main.Version=${version} -X main.GitCommitHash=${gitCommitHash} -X main.BuildDateTime=${buildDateTime}"  -o "bin/${exeName}"
	fEcho_ResetBlankCounter

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
	fEcho_ResetBlankCounter

	## Format
	fEcho "Formatting ..."
	gofmt -w -s . | ts "    "  ## Or -l instead of -d to only show what files changed.
	fEcho_ResetBlankCounter

	## Verify
	fEcho "Verifying ... $(go mod verify)"
	fEcho_ResetBlankCounter

	## Stastic analysis
	fEcho "Vetting ..."
	go vet . | ts "    "
	fEcho_ResetBlankCounter

	## Linting
	fEcho "Linting ..."
	golint . | ts "    "
	fEcho_ResetBlankCounter

	## Build
	fEcho "Building ..."
	fEcho
	fBuild
	fEcho_ResetBlankCounter

	## Validate
	if [[ ! -f "bin/${exeName}" ]]; then fThrowError "Not found: 'bin/${exeName}'."; fi

	## Compress
	fEcho "Shrinking ..."
	[[   -f "bin/${exeName}"      ]] && mv  "bin/${exeName}"  "bin/${exeName}_uncompressed"
#	upx  -qq --ultra-brute  -o"bin/${exeName}"  "bin/${exeName}_uncompressed"
	upx  -qq                -o"bin/${exeName}"  "bin/${exeName}_uncompressed" | ts "    "
	fEcho_ResetBlankCounter
	fEcho

	## Show
	LC_COLLATE="C" ls -lA --color=always --group-directories-first --human-readable --indicator-style=slash --time-style=+"%Y-%m-%d %H:%M:%S" "bin"
	fEcho_ResetBlankCounter

	## Test
	fEcho
	fEcho "Test run ..."
	fEcho_Clean "-------------------------------------------------------------------------------"
	"bin/${exeName}"
	fEcho_ResetBlankCounter
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


function fStrNormalize_byecho(){
	local argStr="$*"
	argStr="$(echo -e "${argStr}")" #.................................................................. Convert \n and \t to real newlines, etc.
	argStr="${argStr//$'\n'/ }" #...................................................................... Convert newlines to spaces
	argStr="${argStr//$'\t'/ }" #...................................................................... Convert tabs to spaces
	argStr="$(echo "${argStr}" | awk '{$1=$1};1' 2>/dev/null || true)" #............................... Collapse multiple spaces to one and trim
	argStr="$(echo "${argStr}" | sed 's/^[[:blank:]]*//;s/[[:blank:]]*$//' 2>/dev/null || true)" #..... Additional trim
	echo "${argStr}"
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
function fEcho_Clean_If(){
	local -r prefix="$1"
	local -r middleIf="$2"
	local -r postfix="$3"
	if [[ -n "${middleIf}" ]]; then fEcho_Clean "${prefix}${middleIf}${postfix}"; fi
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