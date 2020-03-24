package settings

import (
	"testing"
	"github.com/stretchr/testify/assert"
)

func TestSettings(t *testing.T) {
	assert.True(t, NamehelpSettings.ResolvConfig.Interval > 0,
		"settings.ResolvConfig.Interval must be strictly greater than 0.")
}
