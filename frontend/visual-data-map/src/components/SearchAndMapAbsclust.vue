<script setup>

</script>

<script>

import httpClient from '../api/httpClient';

export default {
  data() {
    return {
      query: "",
      search_results: [],
      search_timings: "",
      map_html: "",
      map_js: "",
      map_timings: "",
      cluster_uids: [],
    }
  },
  methods: {
    submit_query(event) {
      // `this` inside methods points to the current active instance
      const that = this  // not sure if neccessary


      that.search_results = []
      that.search_timings = []
      that.map_html = ""
      that.map_js = ""
      that.cluster_uids = []
      that.map_timings = []

      const payload = {
        query: this.query,
      }

      httpClient.post("/api/query", payload)
        .then(function (response) {
          that.search_results = response.data["items"]
          that.search_timings = response.data["timings"]
          that.map_timings = []
          that.map_html = ""

          httpClient.post("/api/map", payload)
            .then(function (response) {
              that.map_html = response.data["html"]
              that.map_js = response.data["js"]
              that.cluster_uids = response.data["cluster_uids"]
              that.map_timings = response.data["timings"]
              setTimeout(() => {
                eval(response.data["js"])
              }, 200)
            })
        })
    },
    show_cluster(cluster_item) {
      this.query = `cluster_id: ${cluster_item.cluster_id} (${cluster_item.cluster_title})`
      this.submit_query()
    }
  }
}

</script>

<template>
  <!-- <header class="bg-white shadow">
      <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">Search & Map</h1>
      </div>
    </header> -->
    <main>
      <div class="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">


        <label for="search" class="block text-sm font-medium leading-6 text-gray-900">
          Searching in subset of 5M (of 20M) PubMed articles using vector and BM25 hybrid search
        </label>

        <!-- search event is not standard -->
          <div class="relative mt-2 w-2/3 rounded-md shadow-sm">
              <input type="search" name="search" @search="submit_query" v-model="query"
              placeholder="Search"
              class="block w-full rounded-md border-0 py-1.5 text-gray-900 ring-1
            ring-inset ring-gray-300 placeholder:text-gray-400
            focus:ring-2 focus:ring-inset focus:ring-indigo-600
            sm:text-sm sm:leading-6" />
          </div>
        <br>

        <div class="grid grid-cols-2 gap-4">
          <div>

            <ul role="list" class="">
              <li v-for="item in search_results" :key="item.title" class="flex justify-between py-2">
                <div class="min-w-0 flex-auto rounded-md shadow-sm bg-white p-3">
                  <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="item.title"></div></p>
                  <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.container_title }}, {{ item.issued_year.toFixed(0) }}</p>
                  <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.most_important_words }}</p>
                  <p class="mt-2 text-xs leading-5 text-gray-700"><div v-html="item.abstract"></div></p>
                </div>
              </li>
            </ul>


            <ul role="list" class="">
              <li v-for="item in search_timings" :key="item.part" class="text-gray-300">
                {{ item.part }}: {{ item.duration.toFixed(2) }} s
              </li>
            </ul>
          </div>

          <div>
            <div v-html="map_html" style="height: 450px"></div>

            <ul role="list" class="">
              <li v-for="item in cluster_uids" :key="item.part" class="">
                <button @click="show_cluster(item)" class="m-3 bg-blue-500 hover:bg-blue-700 text-white py-2 px-4 rounded">
                  {{ item.cluster_title }}
                </button>
              </li>
            </ul>

            <ul role="list" class="">
              <li v-for="item in map_timings" :key="item.part" class="text-gray-300">
                {{ item.part }}: {{ item.duration.toFixed(2) }} s
              </li>
            </ul>
          </div>
        </div>

      </div>
    </main>
</template>

<style scoped></style>
