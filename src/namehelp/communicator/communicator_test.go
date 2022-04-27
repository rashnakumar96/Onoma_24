package communicator

import (
	"fmt"
	"testing"
)

func TestFetcher(t *testing.T) {
	communicator := NewFetcher()
	data, err := communicator.FetchOne("SourceData", "public_dns", map[string]string{"country": "AL"})
	if err != nil {
		fmt.Println(err)
	}
	for k, v := range data {
		fmt.Println(k, v)
	}
}
