<script setup>

import InteractiveMap from "./InteractiveMap.vue"
import ClusterLabels from "./ClusterLabels.vue"
import CloseUpPointItems from "./CloseUpPointItems.vue"
import LassoArea from "./LassoArea.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>


export default {
  inject: ["eventBus"],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="relative">

    <InteractiveMap
      class="absolute w-full h-full"
      @point_selected="appState.show_document_details" />

    <div v-if="mapState.is_polar"
      class="pointer-events-none absolute"
      :style="{
        left: mapState.mapLeftFromRelative(0) - ((mapState.mapLeftFromRelative(2) - mapState.mapLeftFromRelative(0)) / 2) + 'px',
        bottom: mapState.mapBottomFromRelative(0) - ((mapState.mapLeftFromRelative(2) - mapState.mapLeftFromRelative(0)) / 2) + 'px',
        width: mapState.mapLeftFromRelative(2) - mapState.mapLeftFromRelative(0) + 'px',
        height: mapState.mapLeftFromRelative(2) - mapState.mapLeftFromRelative(0) + 'px',
      }">
      <div class="absolute h-full w-full border border-blue-500 rounded-full opacity-50"></div>
      <div class="absolute h-full w-full scale-50 border border-blue-500 rounded-full opacity-50"></div>
      <div class="absolute h-full w-full scale-[0.25] border border-blue-500 rounded-full opacity-50"></div>
    </div>

    <CloseUpPointItems class="absolute w-full h-full" />

    <ClusterLabels class="absolute w-full h-full" />

    <LassoArea class="absolute w-full h-full" />
  </div>
</template>

<style scoped></style>
