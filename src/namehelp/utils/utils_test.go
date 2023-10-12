package utils

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestUnionStringLists(t *testing.T) {
	list1 := []string{"hello", "goodbye"}
	list2 := []string{"hello1", "goodbye", "farewell"}

	result := UnionStringLists(list1, list2)
	gold := []string{"hello1", "goodbye", "farewell", "hello"}
	assert.Equal(t, gold, result, "Expected %v. Got %v", gold, result)

	result = UnionStringLists(list2, list1)
	assert.Equal(t, gold, result, "Expected %v. Got %v", gold, result)
}

func TestUnionStringLists2(t *testing.T) {
	list1 := []string{"8.8.8.8", "4.2.2.5", "208.67.222.222", "192.168.0.1", "Direct Resolution"}
	list2 := []string{"192.168.0.1"}
	list3 := []string{"Direct Resolution"}

	result := UnionStringLists(list1, list2)
	result = UnionStringLists(result, list3)

	gold := list1
	assert.Equal(t, gold, result, "Expected: %v Got %v", gold, result)

	result = UnionStringLists(list2, list3)
	result = UnionStringLists(result, list1)
	assert.Equal(t, gold, result, "Expected: %v Got %v", gold, result)
}

func TestCombineStringMaps(t *testing.T) {
	map1 := map[string]string{}
	map2 := map[string]string{"key1": "value1"}

	var result map[string]string

	result = CombineStringMaps(map1, map2)
	assert.Equal(t, map2, result, "result map [%v] should be [%v]", result, map2)

	result = CombineStringMaps(map2, map1)
	assert.Equal(t, map2, result, "result map [%v] should be [%v]", result, map2)

	map3 := map[string]string{"key2": "value2", "key3": "value3"}
	result = CombineStringMaps(map2, map3)
	gold := map[string]string{"key1": "value1", "key2": "value2", "key3": "value3"}
	assert.Equal(t, map3, gold, "result map [%v] should be [%v]", result, gold)
}

func TestPathExists(t *testing.T) {
	check := PathExists("/sa;lkfj/;salkfjd/a;sldkf")
	assert.False(t, check, "%s should not exist.", check)
}

func TestQueryPublicIpInfo(t *testing.T) {
	ipInfo, _ := QueryPublicIpInfo()
	print(ipInfo.Country)
}

func TestGetObliviousDnsRequest(t *testing.T) {
	GetObliviousDnsRequest()
}

func TestCheckUniqueWebsites(t *testing.T) {
	website := "goodgames.com.au"
	assert.True(t, CheckUniqueWebsites(website))
}
