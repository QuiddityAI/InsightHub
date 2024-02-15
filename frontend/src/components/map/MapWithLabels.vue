<script setup>

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import InteractiveMap from "./InteractiveMap.vue"
import ClusterLabels from "./ClusterLabels.vue"
import HoverLabel from "./HoverLabel.vue"

const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>


export default {
  inject: ["eventBus"],
  emits: ["cluster_selected", "point_selected", "cluster_hovered", "cluster_hover_end"],
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
  <div>
    <InteractiveMap
      class="absolute top-0 h-screen w-screen"
      @point_selected="appState.show_document_details" />

    <ClusterLabels class="absolute top-0 h-screen w-screen" />

    <HoverLabel class="absolute top-0 h-screen w-screen" />
  </div>
</template>

<style scoped></style>
