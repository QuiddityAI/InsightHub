<script setup>
import {
  HandThumbUpIcon,
  HandThumbDownIcon,
 } from "@heroicons/vue/24/outline"

import ProgressSpinner from 'primevue/progressspinner';

import { httpClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>
export default {
  props: ["initial_item", "rendering", "index"],
  emits: ["selected"],
  data() {
    return {
      item: this.initial_item,
      loading_item: false,
      body_text_collapsed: true,
      show_more_button: false,
      loading_relevancy: false,
      relevancy: null,
    }
  },
  watch: {
    initial_item() {
      this.item = this.initial_item
      this.relevancy = null
      this.getFullItem()
      this.get_relevancy(this.index * 500)
    },
  },
  methods: {
    getFullItem() {
      if (!this.item || !this.item._id) return
      const that = this

      const payload = {
        dataset_id: this.item._dataset_id,
        item_id: this.item._id,
        fields: this.appStateStore.datasets[this.item._dataset_id].schema.result_list_rendering.required_fields,
      }
      this.loading_item = true
      httpClient
        .post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item = {
            ...that.item,
            ...response.data,
          }
          // height of text is only available after rendering:
          setTimeout(() => {
            that.show_more_button = that.$refs.body_text?.scrollHeight > that.$refs.body_text?.clientHeight
          }, 100)
        })
        .finally(function () {
          that.loading_item = false
        })
    },
    get_relevancy(delay) {
      if (!this.item || !this.item._id) return
      if (!this.appStateStore.logged_in) return
      const that = this

      const question = this.mapStateStore.map_parameters?.search.question || this.mapStateStore.map_parameters?.search.all_field_query
      if (!question) return

      const payload = {
        user_id: this.appStateStore.user.id,
        dataset_id: this.item._dataset_id,
        item_id: this.item._id,
        question: question,
        delay: delay,
      }
      this.loading_relevancy = true
      httpClient
        .post("/org/data_map/judge_item_relevancy_using_llm", payload)
        .then(function (response) {
          that.relevancy = response.data
        })
        .finally(function () {
          that.loading_relevancy = false
        })
    },
  },
  mounted() {
    this.getFullItem()
    this.show_more_button = this.$refs.body_text?.scrollHeight > this.$refs.body_text?.clientHeight
    this.get_relevancy(this.index * 500)
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
  }
}
</script>

<template>
  <div class="rounded bg-gray-100/50 p-3 flex flex-row gap-2"
    :class="{'opacity-30': relevancy && relevancy.decision === false }">
    <div class="flex-1">
      <button class="flex flex-row text-left" @click="$emit('selected')">
        <img v-if="rendering.icon(item)" :src="rendering.icon(item)" class="h-5 w-5 mr-2" />
        <p class="text-md font-medium leading-tight text-sky-800 hover:underline" v-html="rendering.title(item)"></p>
      </button>
      <p class="mt-1 text-xs leading-normal text-gray-500" v-html="rendering.subtitle(item)"></p>

      <p ref="body_text" class="mt-2 text-[13px] text-gray-700" :class="{ 'line-clamp-[6]': body_text_collapsed }"
       v-html="rendering.body(item)"></p>
      <div class="flex flex-row items-begin">
        <div v-if="show_more_button" class="mt-2 text-xs text-gray-700">
          <button @click.prevent="body_text_collapsed = !body_text_collapsed" class="text-gray-500">
            {{ body_text_collapsed ? "Show more" : "Show less" }}
          </button>
        </div>
        <div class="flex-1"></div>
        <div v-if="loading_relevancy" class="flex flex-row items-center">
          <ProgressSpinner class="w-4 h-4"></ProgressSpinner>
        </div>
        <div v-else-if="relevancy" class="flex flex-row items-center"
          v-tooltip="{'value': relevancy.explanation }">
          <HandThumbUpIcon class="w-4 h-4 text-green-500" v-if="relevancy.decision" />
          <HandThumbDownIcon class="w-4 h-4 text-red-500" v-else />
        </div>
      </div>



      <!-- <p class="mt-2 text-xs leading-5 text-gray-700" v-if="rendering.url(item)">
        <a :href="rendering.url(item)">Link</a>
      </p> -->
      <span v-if="mapState.map_parameters?.search.dataset_ids.length > 1" class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
        {{ appState.datasets[item._dataset_id].name }}
      </span>
      <div v-if="appState.dev_mode" class="flex flex-col gap-1">
        <span
          v-for="origin in item._origins"
          class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
          r: {{ origin.rank }}, s: {{ origin.score.toFixed(2) }},
          {{ origin.type }}<span v-if="origin.field">: {{ origin.field }}</span>
          <span v-if="origin.query">, q: {{ origin.query }}</span>
        </span>
        <!-- <span class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
          {{ item._highlights }}
        </span> -->
      </div>
    </div>
    <button v-if="rendering.image(item)" class="flex-none w-32 flex flex-col justify-center"
      @click="$emit('selected')">
      <img class="w-full rounded-lg shadow-md" :src="rendering.image(item)" />
    </button>
  </div>
</template>
