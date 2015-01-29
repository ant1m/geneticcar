package main

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"math"
	"math/rand"
	"net/http"
	"reflect"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

var voitures = NewPopulation()
var r = rand.New(rand.NewSource(int64(time.Now().Nanosecond())))

func main() {
	winner := make([]float32, 24)
	for {
		r = rand.New(rand.NewSource(int64(time.Now().Nanosecond())))
		resp, err := http.Post("http://servergeneticcar.herokuapp.com/simulation/evaluate/YELLOW", "application/json", bytes.NewReader([]byte(voitures.toJson())))
		if err != nil {
			panic(err)
		}
		body, _ := ioutil.ReadAll(resp.Body)
		resp.Body.Close()
		setScores(string(body))

		sort.Sort(voitures)
		if !reflect.DeepEqual(winner, voitures.V[0]) {
			winner := voitures.V[0]
			fmt.Println("Winner changed : ", winner)
		}
		fmt.Println("Max score : ", voitures.V[0][23])
		fmt.Println("Winner : ", voitures.V[0][23])
		voitures.newGeneration()
	}
}

func setScores(response string) {
	re := regexp.MustCompile("score\":([0-9]*)")
	scores := re.FindAllStringSubmatch(response, -1)
	for i, _ := range scores {
		intScore, _ := strconv.Atoi(scores[i][1])
		voitures.V[i][23] = float32(intScore)
	}
}

func getJsonPopulation(v voiture) string {
	generation := fmt.Sprintln("{\"chassi\": { \"densite\": ", v[0], ", \"vecteurs\": [")
	generation = fmt.Sprintln(generation, v[1],
		",", v[2],
		",", v[3],
		",", v[4],
		",", v[5],
		",", v[6],
		",", v[7],
		",", v[8],
		",", v[9],
		",", v[10],
		",", v[11],
		",", v[12],
		",", v[13],
		",", v[14],
		",", v[15],
		",", v[16], "]},\"team\": \"YELLOW\",")
	generation = fmt.Sprintln(generation, "\"wheel2\": {\"radius\": ", v[17], ",\"density\":", v[18], ",\"vertex\":", v[19], "},")
	generation = fmt.Sprintln(generation, "\"wheel1\": {\"radius\": ", v[20], ",\"density\":", v[21], ",\"vertex\":", v[22], "}}")
	return generation
}

type voiture []float32

type population struct {
	V []voiture
}

func (p *population) Len() int {
	return len(p.V)
}

func (p *population) Less(i, j int) bool {
	return p.V[i][23] > p.V[j][23]
}

func (p *population) Swap(i, j int) {
	p.V[i], p.V[j] = p.V[j], p.V[i]
}

func (p *population) newGeneration() {
	for i := 5; i < 10; i++ {
		p.V[i+1], p.V[i] = croise(p.V[i-5], p.V[i-4])
	}
	for i := 10; i < len(p.V); i++ {
		p.V[i] = getVoiture()
	}
}

func NewPopulation() *population {
	p := &population{make([]voiture, 20)}
	for i := 0; i < len(p.V); i++ {
		p.V[i] = getVoiture()
	}
	return p
}

func croise(v1, v2 voiture) (voiture, voiture) {
	index := r.Int31n(22)
	v1[index], v2[index] = v2[index], v1[index]
	return v1, v2
}

func (p *population) toJson() string {
	json := "["
	voitureStr := make([]string, len(p.V))
	for i, _ := range voitures.V {
		voitureStr[i] = getJsonPopulation(voitures.V[i])
	}
	vJson := strings.Join(voitureStr, ",")
	json = fmt.Sprintln(json, vJson, "]")
	return json
}

func getVoiture() voiture {
	v := make([]float32, 24)
	index := 0
	v[index] = densité(r.Float32())
	index++

	v[index] = coordonnées(r.Float32())
	index++
	v[index] = 0.0
	index++

	v[index] = coordonnées(r.Float32())
	index++
	v[index] = coordonnées(r.Float32())
	index++

	v[index] = 0.0
	index++
	v[index] = coordonnées(r.Float32())
	index++

	v[index] = -coordonnées(r.Float32())
	index++
	v[index] = coordonnées(r.Float32())
	index++

	v[index] = -coordonnées(r.Float32())
	index++
	v[index] = 0.0
	index++

	v[index] = -coordonnées(r.Float32())
	index++
	v[index] = -coordonnées(r.Float32())
	index++

	v[index] = 0.0
	index++
	v[index] = -coordonnées(r.Float32())
	index++

	v[index] = coordonnées(r.Float32())
	index++
	v[index] = -coordonnées(r.Float32())
	index++

	v[index] = rayon(r.Float32())
	index++
	v[index] = densitéRoue(r.Float32())
	index++
	v[index] = sommet(r.Float32())
	index++
	v[index] = rayon(r.Float32())
	index++
	v[index] = densitéRoue(r.Float32())
	index++
	v[index] = sommet(r.Float32())
	index++
	v[index] = 0
	return v
}

func densité(val float32) float32 {
	return val*(300.0-30.0) + 30.0
}
func densitéRoue(val float32) float32 {
	return val*(100.0-40.0) + 40.0
}
func coordonnées(val float32) float32 {
	return 0.1 + val
}
func rayon(val float32) float32 {
	return val*(0.5-0.2) + 0.2
}
func sommet(val float32) float32 {
	s := val * 7.0
	return float32(math.Ceil(float64(s)))
}
