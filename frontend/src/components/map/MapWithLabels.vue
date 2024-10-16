<script setup>

import InteractiveMap from "./InteractiveMap.vue"
import ClusterLabels from "./ClusterLabels.vue"
import CloseUpPointItems from "./CloseUpPointItems.vue"
import LassoArea from "./LassoArea.vue"
import HoverLabel from "./HoverLabel.vue"

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

    <CloseUpPointItems class="absolute w-full h-full" />

    <ClusterLabels class="absolute w-full h-full" />

    <HoverLabel class="absolute w-full h-full" />

    <LassoArea class="absolute w-full h-full" />
  </div>
</template>

<style scoped></style>
