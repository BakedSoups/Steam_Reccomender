package main

// this file uses all the go "Dags"
import (
	"fmt"
	"strconv"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	appids := steamspy_appids()
	for _, str := range appids {
		fmt.Printf("Value: %d\n", str)

		num := strconv.Itoa(str)

		steamApiPull(num)
	}

}
