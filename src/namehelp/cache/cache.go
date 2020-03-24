// based heavily upon github.com/kenshinx/godns/cache.go

package cache

import (
	"crypto/md5"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/miekg/dns"
)

// KeyNotFound error type
type KeyNotFound struct {
	key string
}

func (e KeyNotFound) Error() string {
	return e.key + " " + "not found"
}

// KeyExpired represents the expired key
type KeyExpired struct {
	Key string
}

func (e KeyExpired) Error() string {
	return e.Key + " " + "expired"
}

// IsFull error type
type IsFull struct {
}

func (e IsFull) Error() string {
	return "Cache is Full"
}

// SerializerError error type
type SerializerError struct {
}

func (e SerializerError) Error() string {
	return "Serializer error"
}

// Mesg stores dns message as value of the cache
type Mesg struct {
	Msg    *dns.Msg
	Expire time.Time
}

// Cache interface
type Cache interface {
	Get(key string) (Msg *dns.Msg, err error)
	Set(key string, Msg *dns.Msg) error
	Exists(key string) bool
	Remove(key string)
	Length() int
}

// MemoryCache represents cache in memory that implements Cache interface
type MemoryCache struct {
	Backend  map[string]Mesg
	Expire   time.Duration
	Maxcount int
	mu       sync.RWMutex
}

// Get returns the value stored in cache matched to the key speficied
func (c *MemoryCache) Get(key string) (*dns.Msg, error) {
	c.mu.RLock()
	mesg, ok := c.Backend[key]
	c.mu.RUnlock()
	if !ok {
		return nil, KeyNotFound{key}
	}

	if mesg.Expire.Before(time.Now()) {
		c.Remove(key)
		return nil, KeyExpired{key}
	}

	return mesg.Msg, nil

}

// Set takes a key value pair and set the value in Cache accordingly
func (c *MemoryCache) Set(key string, msg *dns.Msg) error {
	if c.Full() && !c.Exists(key) {
		return IsFull{}
	}

	expire := time.Now().Add(c.Expire)
	mesg := Mesg{msg, expire}
	c.mu.Lock()
	c.Backend[key] = mesg
	c.mu.Unlock()
	return nil
}

// Remove removes the cache entry specified by the key given
func (c *MemoryCache) Remove(key string) {
	c.mu.Lock()
	delete(c.Backend, key)
	c.mu.Unlock()
}

// Exists checks whether the key exists in the cache
func (c *MemoryCache) Exists(key string) bool {
	c.mu.RLock()
	_, ok := c.Backend[key]
	c.mu.RUnlock()
	return ok
}

// Length returns the length of the cache
func (c *MemoryCache) Length() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.Backend)
}

// Full returns whether the cache is full
func (c *MemoryCache) Full() bool {
	// if Maxcount is zero. the cache will never be full.
	if c.Maxcount == 0 {
		return false
	}
	return c.Length() >= c.Maxcount
}

// KeyGen generates a key for the given dns queston
func KeyGen(q dns.Question) string {
	h := md5.New()
	h.Write([]byte(q.String()[1:]))
	x := h.Sum(nil)
	key := fmt.Sprintf("%x", x)
	return key
}

// Are these leftover from the start of the Redis implementation?
// Or are these actually needed?

// JSONSerializer serialize json objects
type JSONSerializer struct {
}

// Dumps return the encoded bytes as json object format
func (*JSONSerializer) Dumps(mesg *dns.Msg) (encoded []byte, err error) {
	encoded, err = json.Marshal(mesg)
	return
}

// Loads takes data bytes and convert into json object and store in the dns message provided
func (*JSONSerializer) Loads(data []byte, mesg **dns.Msg) error {
	err := json.Unmarshal(data, mesg)
	return err

}
