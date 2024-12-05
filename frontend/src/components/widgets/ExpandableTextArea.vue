<script setup>
import { debounce } from "../../utils/utils"

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ['html_content', 'max_lines'],
  data() {
    return {
      body_text_collapsed: true,
      show_more_button: false,
      update_show_more_button_debounce: debounce((event) => {
        this.update_show_more_button()
      }, 200),
    }
  },
  computed: {

  },
  mounted() {
    this.update_show_more_button_debounce()
  },
  watch: {
    html_content() {
      this.update_show_more_button_debounce()
    },
  },
  methods: {
    update_show_more_button() {
      this.$nextTick(() => {
        this.show_more_button = this.$refs.body_text?.scrollHeight > this.$refs.body_text?.clientHeight
      });
    },
  },
}
</script>


<template>
  <div class="relative text-[13px] text-gray-700">
    <p ref="body_text"
      :class="{ [`line-clamp-[${max_lines}]`]: body_text_collapsed }"
      v-html="html_content">
    </p>
    <div v-if="show_more_button" class="absolute -bottom-1 right-0  pb-[2px] px-2 bg-white"> <!-- rounded-md shadow-[0px_0px_5px_3px_white]> -->
      <button @click.prevent="body_text_collapsed = !body_text_collapsed"
        class="text-xs text-gray-400 underline hover:text-blue-300">
        {{ body_text_collapsed ? "Show more" : "^" }}
      </button>
    </div>
  </div>
</template>