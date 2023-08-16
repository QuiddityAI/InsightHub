<script setup>
import EmbeddingMap from './EmbeddingMap.vue';
</script>

<script>

import httpClient from '../api/httpClient';

import * as math from 'mathjs'

export default {
  data() {
    return {
      query: "",
      search_results: [],
      map_item_details: [],
      search_timings: "",
      map_task_id: null,
      show_loading_bar: false,
      map_viewport_is_adjusted: false,
      progress: 0.0,
      cluster_uids: [],
      map_timings: "",
      windowHeight: 0,

      selectedDocumentIdx: -1,
    }
  },
  methods: {
    submit_query(event) {
      // `this` inside methods points to the current active instance
      const that = this  // not sure if neccessary

      that.selectedDocumentIdx = -1
      that.search_results = []
      that.map_item_details = []
      that.search_timings = []
      that.cluster_uids = []
      that.map_timings = []
      that.$refs.embedding_map.targetPositionsX = []
      that.$refs.embedding_map.targetPositionsY = []
      that.$refs.embedding_map.clusterData = []
      that.$refs.embedding_map.updateGeometry()
      that.map_viewport_is_adjusted = false

      const payload = {
        query: this.query,
      }

      httpClient.post("/api/query", payload)
        .then(function (response) {
          that.search_results = response.data["items"]
          that.search_timings = response.data["timings"]

          httpClient.post("/api/map", payload)
            .then(function (response) {
              that.map_task_id = response.data["task_id"]
              that.map_viewport_is_adjusted = false
            })
        })
    },
    get_mapping_progress() {
      const that = this
      if (!this.map_task_id) {
        setTimeout(function() {
          this.get_mapping_progress()
        }.bind(this), 100);
        return
      }
      const payload = {
        task_id: this.map_task_id,
      }
      httpClient.post("/api/map/result", payload)
        .then(function (response) {
          const finished = response.data["finished"]

          if (finished) {
            // no need to get further results:
            that.map_task_id = null
          }

          const progress = response.data["progress"]

          that.show_loading_bar = !progress.embeddings_available
          that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)

          const result = response.data["result"]

          function normalizeArray(a, gamma=1.0, max_default=1.0) {
            if (a.length === 0) return a;
            a = math.subtract(a, math.min(a))
            return math.dotPow(math.divide(a, math.max(math.max(a), max_default)), gamma)
          }

          function normalizeArrayMedianGamma(a, max_default=1.0) {
            if (a.length === 0) return a;
            a = math.subtract(a, math.min(a))
            a = math.divide(a, math.max(math.max(a), max_default))
            // using the median as gamma should provide a good, balanced distribution:
            const gamma = math.max(0.1, math.median(a) * 0.6)
            return math.dotPow(a, gamma)
          }

          if (result) {
            that.$refs.embedding_map.targetPositionsX = result["per_point_data"]["positions_x"]
            that.$refs.embedding_map.targetPositionsY = result["per_point_data"]["positions_y"]
            that.$refs.embedding_map.clusterIdsPerPoint = result["per_point_data"]["cluster_ids"]
            that.$refs.embedding_map.pointSizes = normalizeArrayMedianGamma(result["per_point_data"]["citations"])
            that.$refs.embedding_map.saturation = normalizeArray(result["per_point_data"]["distances"], 3.0)

            that.map_item_details = result["item_details"]
            that.$refs.embedding_map.itemDetails = result["item_details"]
            that.$refs.embedding_map.clusterData = result["cluster_data"]

            if (that.map_viewport_is_adjusted) {
              that.$refs.embedding_map.centerAndFitDataToActiveAreaSmooth()
            } else {
              that.$refs.embedding_map.resetPanAndZoom()
              that.$refs.embedding_map.centerAndFitDataToActiveAreaInstant()
              that.map_viewport_is_adjusted = true
            }
            that.$refs.embedding_map.updateGeometry()

            that.map_timings = result["timings"]
          }
        })
        .catch(function (error) {
          if (error.response && error.response.status === 404) {
            // no more data for this task, stop polling:
            that.map_task_id = null
            console.log("404 response")
          } else {
            console.log(error)
          }
        })
        .finally(function() {
          setTimeout(function() {
            that.get_mapping_progress()
          }.bind(this), 100);
        })
    },
    show_cluster(cluster_item) {
      this.query = `cluster_id: ${cluster_item.uid} (${cluster_item.title})`
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
    show_document_details(pointIdx) {
      this.selectedDocumentIdx = pointIdx
      this.$refs.embedding_map.selectedPointIdx = pointIdx
    },
    close_document_details() {
      this.selectedDocumentIdx = -1
      this.$refs.embedding_map.selectedPointIdx = -1
    },
  },
  mounted() {
    this.updateMapPassiveMargin()
    window.addEventListener("resize", this.updateMapPassiveMargin)

    this.get_mapping_progress()
  },
  updated() {
    this.updateMapPassiveMargin()
  },
}

</script>

<template>

    <main>

      <div class="absolute top-0 w-screen h-screen">
        <EmbeddingMap ref="embedding_map" @show_cluster="show_cluster" @point_selected="show_document_details"/>
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
                <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="item.title_enriched"></div></p>
                <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.container_title }}, {{ item.issued_year.toFixed(0) }}</p>
                <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.most_important_words }}</p>
                <p class="mt-2 text-xs leading-5 text-gray-700"><div v-html="item.abstract_enriched"></div></p>
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

          <div class="h-8"></div>

          <div v-if="selectedDocumentIdx !== -1 && map_item_details.length > selectedDocumentIdx" class="pointer-events-auto w-full">
            <div class="min-w-0 flex-auto rounded-md shadow-sm bg-white p-3">
                <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="map_item_details[selectedDocumentIdx].title"></div></p>
                <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ map_item_details[selectedDocumentIdx].container_title }}, {{ map_item_details[selectedDocumentIdx].issued_year.toFixed(0) }}</p>
                <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ map_item_details[selectedDocumentIdx].most_important_words }}</p>
                <p class="mt-2 text-xs leading-5 text-gray-700"><div v-html="map_item_details[selectedDocumentIdx].abstract_enriched"></div></p>
                <button @click="close_document_details" class="px-3 py-1 bg-blue-600/50 hover:bg-blue-600 rounded">Close</button>
              </div>
          </div>

          <div class="flex" :style="{height: (windowHeight - 150) + 'px'}">
            <div v-if="show_loading_bar" class="self-center w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
              <div class="bg-blue-600 h-2.5 rounded-full" :style="{'width': (progress * 100).toFixed(0) + '%'}"></div>
            </div>
          </div>

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
