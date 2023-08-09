<script setup>
import EmbeddingMap from './EmbeddingMap.vue';
</script>

<script>

import httpClient from '../api/httpClient';

export default {
  data() {
    return {
      query: "",
      search_results: [],
      search_timings: "",
      cluster_uids: [],
      map_timings: "",
      windowHeight: 0,
    }
  },
  methods: {
    submit_query(event) {
      // `this` inside methods points to the current active instance
      const that = this  // not sure if neccessary

      that.search_results = []
      that.search_timings = []
      that.cluster_uids = []
      that.map_timings = []
      // TODO: clear map

      const payload = {
        query: this.query,
      }

      httpClient.post("/api/query", payload)
        .then(function (response) {
          that.search_results = response.data["items"]
          that.search_timings = response.data["timings"]

          httpClient.post("/api/map", payload)
            .then(function (response) {
              that.cluster_uids = response.data["cluster_uids"]
              that.map_timings = response.data["timings"]

              that.$refs.embedding_map.currentPositionsX = response.data["per_point_data"]["positionsX"]
              that.$refs.embedding_map.currentPositionsY = response.data["per_point_data"]["positionsY"]
              that.$refs.embedding_map.cluster_ids = response.data["per_point_data"]["cluster_ids"]
              that.$refs.embedding_map.updateMap()
            })
        })
    },
    show_cluster(cluster_item) {
      this.query = `cluster_id: ${cluster_item.cluster_id} (${cluster_item.cluster_title})`
      this.submit_query()
    },
    updateMapPassiveMargin() {
      this.windowHeight = window.innerHeight

      this.$refs.embedding_map.passiveMarginsLRTB = [
        this.$refs.left_column.getBoundingClientRect().right + 50,
        window.innerWidth - this.$refs.right_column.getBoundingClientRect().right,
        50,
        150
      ]
    },
  },
  mounted() {
    this.updateMapPassiveMargin()
    window.onresize = this.updateMapPassiveMargin
  },
  updated() {
    this.updateMapPassiveMargin()
  },
}

</script>

<template>

    <main>

      <div class="absolute top-0 w-screen h-screen">
        <EmbeddingMap ref="embedding_map"/>
      </div>

      <!-- <div v-show="search_results && !map_html" class="absolute flex top-1/2 left-2/3 items-center">
        <div class="relative h-8 w-8 block">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-8 w-8 bg-sky-500 opacity-50"></span>
        </div>
      </div> -->

      <!-- content area -->
      <div class="relative h-screen mx-auto max-w-7xl sm:px-6 lg:px-8 grid grid-cols-2 gap-4 pointer-events-none">

        <!-- left column -->
        <div ref="left_column" class="overflow-y-auto pointer-events-auto">

          <div class="h-8"></div>

          <!-- search card -->
          <div class="sticky top-0 rounded-md shadow-sm bg-white p-3">
            <div class="flex justify-between">
              <select class="pl-2 pr-8 pt-1 pb-1 mb-2 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
                <option value="absclust" selected>AbsClust Database</option>
                <option value="pubmed">PubMed</option>
              </select>
              <span class="pl-2 pr-2 pt-1 pb-1 mb-2 text-gray-500 text-sm text-right">60 Million Items</span>
            </div>

            <!-- note: search event is not standard -->
            <div class="relative rounded-md shadow-sm">
                <input type="search" name="search" @search="submit_query" v-model="query"
                placeholder="Search"
                class="block w-full rounded-md border-0 py-1.5 text-gray-900 ring-1
              ring-inset ring-gray-300 placeholder:text-gray-400
              focus:ring-2 focus:ring-inset focus:ring-indigo-600
              sm:text-sm sm:leading-6" />
            </div>
          </div>

          <!-- result list -->
          <ul role="list">
            <li v-for="item in search_results" :key="item.title" class="flex justify-between py-2">
              <div class="min-w-0 flex-auto rounded-md shadow-sm bg-white p-3">
                <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="item.title"></div></p>
                <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.container_title }}, {{ item.issued_year.toFixed(0) }}</p>
                <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.most_important_words }}</p>
                <p class="mt-2 text-xs leading-5 text-gray-700"><div v-html="item.abstract"></div></p>
              </div>
            </li>
          </ul>

          <!-- timings -->
          <ul role="list">
            <li v-for="item in search_timings" :key="item.part" class="text-gray-300">
              {{ item.part }}: {{ item.duration.toFixed(2) }} s
            </li>
          </ul>

          <div class="h-4"></div>
        </div>

        <!-- right column (e.g. for showing box with details for selected result) -->
        <div ref="right_column" class="overflow-y-auto pointer-events-none">

          <div :style="{height: (windowHeight - 150) + 'px'}"></div>

          <ul role="list" class="pointer-events-auto">
            <li v-for="item in cluster_uids" :key="item.part" class="">
              <button @click="show_cluster(item)" class="m-3 bg-blue-500 hover:bg-blue-700 text-white py-2 px-4 rounded">
                {{ item.cluster_title }}
              </button>
            </li>
          </ul>

          <ul role="list">
            <li v-for="item in map_timings" :key="item.part" class="text-gray-300">
              {{ item.part }}: {{ item.duration.toFixed(2) }} s
            </li>
          </ul>
        </div>

      </div>

      <!--  -->
    </main>
</template>

<style scoped></style>
