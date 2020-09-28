package main

import (
	"fmt"
	//	"rsc.io/quote"
)

// Version is for x9go_build
var Version string

// GitCommitHash is for x9go_build
var GitCommitHash string

// BuildDateTime is for x9go_build
var BuildDateTime string

func main() {
	fmt.Println("Version ...........: ", Version)
	fmt.Println("Git commit hash ...: ", GitCommitHash)
	fmt.Println("Build date/time ...: ", BuildDateTime)
}
