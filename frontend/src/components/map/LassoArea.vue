<script setup>
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
    lasso_points_str() {
      return this.mapStateStore.lasso_points
        .map((p) => `${this.mapStateStore.mapLeftFromRelative(p[0])},${this.mapStateStore.mapTopFromRelative(p[1])}`)
        .join(" ")
    },
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
  <svg
      v-if="lasso_points_str"
      id="lasso_area"
      class="pointer-events-none"
      xmlns="http://www.w3.org/2000/svg">
      <polygon
        :points="lasso_points_str"
        style="
          fill: rgba(150, 178, 224, 0.329);
          stroke: rgba(103, 103, 103, 0.478);
          stroke-width: 3;
          stroke-dasharray: 3, 7;
          stroke-linecap: round;
        " />
    </svg>
</template>

<style scoped></style>
